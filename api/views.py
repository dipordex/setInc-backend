# Python standard library imports
import os
import pytz
import random
import logging
from datetime import datetime, timedelta

# Django imports
from django.views import View
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404

# Third-party imports
from fcm_django.models import FCMDevice
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status, permissions
from inapppy import errors, InAppPyValidationError, AppStoreValidator, GooglePlayVerifier
from django.db.models import Count

# Local application imports
from . import api_docs, constants
from messages import ErrorMessages
from tools.sms_tools import twilio
from task.permissions import IsTaskOwner
from .service import TaskUpdateService
from services.top_activities import TopActivitiesService
from .utils import get_token_for_user, beautify_duration, user_soft_delete
from .tasks import schedule_task_notification, get_timezone
from .constants import STOPWATCH_LAPS
from services.task_progress_charts import TaskProgressChartsService
from .validators import user_friendly_timezone_to_iana, validate_date_and_time
from .models import User, VerificationCode, Task, TaskCategory, DefaultAlarm, Quote, Stopwatch, Lap, Receipt
from .serializers import PhoneNumberSerializer, PhoneNumberAndCodeSerializer, UserSerializer, TaskSerializer, \
    TaskCategoriesSerializer, DefaultAlarmSerializer, QuotesSerializer, FCMTokenSerializer, \
    TaskNamesListSerializer, StopwatchSerializer, LapSerializer, ReceiptSerializer
from xhtml2pdf import pisa
from io import BytesIO
from html2image import Html2Image
from .models import Stopwatch
from .serializers import StopwatchSerializer
logger = logging.getLogger(__name__)
from django.template.loader import get_template
from rest_framework.permissions import AllowAny
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from socket_instance import sio
from rest_framework import status as http_status
from django.db.models import (
    Count, ExpressionWrapper, F, DurationField, Case, When, Value, IntegerField
)
from django.db.models.functions import Now, ExtractDay, ExtractHour, ExtractMinute, ExtractSecond


UserModel = get_user_model()


def check_subscription(request) -> bool:
    # Check if the user has a subscription
    if not request.user.has_subscription:
        return False

    # Check if the user has a receipt
    if not hasattr(request.user, 'receipt'):
        return False

    # Ensure payment_expires is timezone-aware and in UTC
    payment_expires = request.user.receipt.payment_expires

    # If payment_expires is naive (no timezone), make it timezone-aware (convert to server time)
    if timezone.is_naive(payment_expires):
        payment_expires = timezone.make_aware(payment_expires, timezone.get_current_timezone())

    # Convert to UTC for comparison
    payment_expires_utc = payment_expires.astimezone(pytz.UTC)
    # Check if the payment expiration date is in the future and user has a subscription
    if payment_expires_utc > datetime.now(tz=pytz.UTC):
        return True

    # If the subscription is expired, update and save
    request.user.receipt.status = "expired"
    request.user.has_subscription = False
    request.user.save()
    request.user.receipt.save()
    return False


class MainView(View):
    template = 'index.html'

    def get(self, request):
        context = {}
        return render(request, self.template, {'context': context})


class GetVerificationCodeAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PhoneNumberSerializer

    @swagger_auto_schema(
        tags=['Verification Code'],
        operation_summary="Get Verification Code",
        operation_description=api_docs.PHONE_CODE_OPERATION_DESCRIPTION,
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data.get('phone_number')
        VerificationCode.objects.filter(phone_number=phone_number).delete()

        if phone_number in twilio.get_test_numbers():
            verification_code = '1111'
        else:
            verification_code = random.randint(1000, 9999)
            twilio.send_verification_code(phone_number, verification_code)

        VerificationCode.objects.create(phone_number=phone_number, verification_code=verification_code)
        return Response({'success': 'The verification code is sent'}, status=status.HTTP_200_OK)


class VerifyVerificationCodeAPI(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PhoneNumberAndCodeSerializer
    queryset = VerificationCode.objects.all()

    @swagger_auto_schema(
        tags=['Verification Code'],
        operation_summary="Verify Verification Code",
        operation_description=api_docs.PHONE_NUMBER_OPERATION_DESCRIPTION,
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_phone_number = serializer.validated_data.get('phone_number')
        request_verification_code = serializer.validated_data.get('verification_code')
        phone_number = get_object_or_404(self.get_queryset(),
                                         phone_number=request_phone_number)

        if phone_number.verification_code == request_verification_code:
            phone_number.verified = True
            phone_number.save()
            user = User.objects.filter(phone_number=request_phone_number).first()
            if user:
                user.is_active = True
                user.save()
                tokens = get_token_for_user(user)
                new_user = {'new_user': False if user.name else True}
                phone_number.delete()
                return Response({**tokens, **new_user})

            created_user = User.objects.create(phone_number=request_phone_number)
            tokens = get_token_for_user(created_user)
            new_user = {'new_user': True}
            phone_number.delete()
            return Response({**tokens, **new_user})

        return Response({'detail': {'error': "Wrong code!"}}, status=status.HTTP_400_BAD_REQUEST)


class UserAPI(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)

        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, data=request.data,
                                         partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        if check_subscription(request):
            user_soft_delete(request.user)
        else:
            self.perform_destroy(request.user)
        return Response(status=status.HTTP_200_OK)


class CreateTaskAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer
    tags = ['Tasks']

    def post(self, request):
        # CHECK SUBSCRIPTIONS
        if not check_subscription(request) and request.user.tasks.count() >= constants.COUNT_UNSUBSCRIBED_TASKS:
            raise ValidationError(ErrorMessages.TASK_CREATE_ERROR, status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # CHANGE TIMEZONES AND VALIDATE DATE
        data = serializer.validated_data
        time_zone, _ = user_friendly_timezone_to_iana(data.get('time_zone'), request.user)
        validate_date_and_time(time_zone, data.get('date'), data.get("start_time"), data.get("end_time"))
        task = serializer.save(user=request.user, time_zone=time_zone)

        if task.send_notification:
            schedule_task_notification.send_with_options(args=(task.id,))
        return Response(serializer.data)


class TaskAPI(generics.GenericAPIView):
    permission_classes = [IsTaskOwner]
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.all()

    def get_object(self):
        task = super().get_object()
        self.check_object_permissions(self.request, task)
        return task

    def get(self, request, pk):
        return Response(self.get_serializer(self.get_object()).data)

    def patch(self, request, pk):
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data, partial=True)

        if serializer.is_valid():
            service = TaskUpdateService(task=task, user=request.user)
            task = service.update_task(serializer.validated_data)
            return Response(self.get_serializer(task).data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        task = self.get_object()
        task.delete()
        return Response(status=status.HTTP_200_OK)


class TasksListByDateAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer
    queryset = Task.objects.all()
    tags = ['Tasks']

    def get(self, request, date: str):
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return Response(ErrorMessages.INCORRECT_DATE_FORMAT, status=status.HTTP_400_BAD_REQUEST)
        user_tasks = self.get_queryset().filter(user=request.user)
        tasks_on_date = user_tasks.filter(date=date)
        serializer = self.get_serializer(tasks_on_date, many=True)

        result = {
            'tasks': serializer.data,
            'tasks_count': user_tasks.count()
        }
        return Response(result, status=status.HTTP_200_OK)


class TasksListAPI(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskNamesListSerializer

    def get_queryset(self):
        if check_subscription(self.request):
            return self.request.user.tasks.filter(done=False)
        else:
            return self.request.user.tasks.filter(done=False)[:constants.COUNT_UNSUBSCRIBED_TASKS]


class TaskCategoriesAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        task_categories = TaskCategory.objects.all()
        serializer = TaskCategoriesSerializer(task_categories, many=True)

        return Response(serializer.data)


class DefaultAlarmAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DefaultAlarmSerializer

    def get(self, request):
        alarm = get_object_or_404(DefaultAlarm, user=request.user)
        serializer = self.get_serializer(alarm)

        return Response(serializer.data)

    def patch(self, request):
        if not DefaultAlarm.objects.filter(user=request.user).exists():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
        else:
            serializer = self.get_serializer(request.user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(serializer.data)


class TaskProgressChartsAPI(APIView):
    def get(self, request):
        try:
            task_service = TaskProgressChartsService(request.user)
            return Response({
                'task_progress_today': task_service.task_progress_today(),
                'progress_chart': task_service.get_task_progress(task_service.get_today()),
                'quotes': QuotesSerializer(Quote.objects.order_by('?')[:3], many=True).data,
                'upcoming_task': task_service.get_upcoming_task(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(ErrorMessages.TASK_TIME_ZONE_ERROR.format(e), exc_info=True)
            return Response({'error': str(ErrorMessages.SOMETHING_WENT_WRONG)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TopActivitiesChartsAPI(APIView):
    def get(self, request):
        today = datetime.now(get_timezone(request.user.timezone)).date()
        task_repository = TopActivitiesService()
        all_task_categories = task_repository.get_all_task_categories()
        user_tasks = task_repository.get_tasks_for_user(user=request.user)
        time_tracked = {}
        current_month_tracked_time = {}
        yearly_tracked_time = {}
        daily_top_activities = {}
        monthly_top_activities = {}

        top_activities = task_repository.get_top_activities(today, user_tasks)

        # Time tracked
        tasks = user_tasks.filter(date__gte=today - timedelta(
            days=6), date__lte=today)
        all_tracked_time = tasks.aggregate(Sum('tracked_time')).get(
            'tracked_time__sum')

        for category in all_task_categories:
            time_tracked[category.name] = {}
            time_tracked_sum = tasks.filter(
                category=category).aggregate(Sum('tracked_time')).get(
                'tracked_time__sum')
            time_tracked.get(category.name)['duration'] = beautify_duration(
                time_tracked_sum)

            if all_tracked_time and time_tracked_sum:
                time_tracked.get(category.name)['percentage'] = \
                    round((time_tracked_sum * 100) / all_tracked_time)
            else:
                time_tracked.get(category.name)['percentage'] = 0

        # Month days activities
        month_start_date = today.replace(day=1)
        delta = today - month_start_date
        dates_list = [month_start_date + timedelta(days=x) for x in
                      range(delta.days + 1)]

        for date in dates_list:
            tasks = user_tasks.filter(date=date)
            tasks_count = tasks.count()
            completed_tasks = tasks.filter(done=True)
            completed_tasks_count = tasks.filter(done=True).count()

            date = str(date)
            daily_top_activities[date] = {}
            for category in all_task_categories:
                if tasks_count:
                    daily_top_activities.get(date)['all'] = \
                        round((completed_tasks_count * 100) / tasks_count)
                else:
                    daily_top_activities.get(date)['all'] = 0

                if completed_tasks_count:
                    daily_top_activities.get(date)[
                        category.name] = round((completed_tasks.filter(
                        category=category).count() * 100) / completed_tasks_count)
                else:
                    daily_top_activities.get(date)[
                        category.name] = 0

        current_month_tasks = user_tasks.filter(date__in=dates_list)
        all_tracked_time = current_month_tasks.aggregate(
            Sum('tracked_time')).get('tracked_time__sum')

        for category in all_task_categories:
            current_month_tracked_time[category.name] = {}
            time_tracked_sum = current_month_tasks.filter(
                category=category).aggregate(Sum('tracked_time')).get(
                'tracked_time__sum')
            current_month_tracked_time.get(category.name)[
                'duration'] = beautify_duration(
                time_tracked_sum)

            if all_tracked_time and time_tracked_sum:
                current_month_tracked_time.get(category.name)['percentage'] = \
                    round((time_tracked_sum * 100) / all_tracked_time)
            else:
                current_month_tracked_time.get(category.name)['percentage'] = 0

        # Months activities in a year
        for month in range(1, 13):
            tasks = user_tasks.filter(date__month=month)
            tasks_count = tasks.count()
            completed_tasks = tasks.filter(done=True)
            completed_tasks_count = tasks.filter(done=True).count()

            monthly_top_activities[month] = {}
            for category in all_task_categories:
                if tasks_count:
                    monthly_top_activities.get(month)['all'] = \
                        round((completed_tasks_count * 100) / tasks_count)
                else:
                    monthly_top_activities.get(month)['all'] = 0

                if completed_tasks_count:
                    monthly_top_activities.get(month)[
                        category.name] = round((completed_tasks.filter(
                        category=category).count() * 100) / completed_tasks_count)
                else:
                    monthly_top_activities.get(month)[
                        category.name] = 0

        # Yearly tracked time
        for category in all_task_categories:
            yearly_tracked_time[category.name] = {}
            time_tracked_sum = user_tasks.filter(
                category=category, date__year=today.year).aggregate(
                Sum('tracked_time')).get('tracked_time__sum')

            yearly_tracked_time.get(category.name)[
                'duration'] = beautify_duration(
                time_tracked_sum)

            if all_tracked_time and time_tracked_sum:
                yearly_tracked_time.get(category.name)['percentage'] = \
                    round((time_tracked_sum * 100) / all_tracked_time)
            else:
                yearly_tracked_time.get(category.name)['percentage'] = 0

        return Response({
            'top_activities': top_activities,
            'weekly_tracked_time': time_tracked,
            'daily_top_activities': daily_top_activities,
            'current_month_tracked_time': current_month_tracked_time,
            'monthly_top_activities': monthly_top_activities,
            'yearly_tracked_time': yearly_tracked_time
        })


class ActivateExistingDevices(APIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get(self, request):
        device_id = self.request.query_params.get('device_id')
        if device_id:
            devices = FCMDevice.objects.filter(
                device_id=self.request.query_params.get('device_id'))

            for d in devices:
                d.active = True
                d.save()

        return Response(status=status.HTTP_200_OK)


class DeactivateExistingDevices(APIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]

    def get(self, request):
        device_id = self.request.query_params.get('device_id')
        if device_id:
            devices = FCMDevice.objects.filter(
                device_id=self.request.query_params.get('device_id'))

            for d in devices:
                d.active = False
                d.save()

        return Response(status=status.HTTP_200_OK)


class CheckFCMTokenAPIView(generics.GenericAPIView):
    http_method_names = ["post"]
    serializer_class = FCMTokenSerializer
    permission_classes = [
        permissions.IsAuthenticated
    ]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            fcm = FCMDevice.objects.get(
                device_id=serializer.validated_data.get('device_id'))

            return Response({'registration_id': fcm.registration_id})
        except:
            return Response({'registration_id': None})


class TimezoneListView(APIView):
    permission_classes = [IsAuthenticated]
    tags = ['Timezones']
    """
    API endpoint that lists all available time zones without their continent prefixes and includes their GMT offsets.

    This endpoint returns a list of time zone names modified to remove any continent prefix. Each time zone name is
    followed by its GMT offset, formatted as `GMT+HH:MM` or `GMT-HH:MM`, where HH is the hour offset and MM is the
    minute offset from GMT.
    """

    def get(self, request, format=None):
        """
        Responds to GET requests with a list of formatted time zones and their GMT offsets.
        """
        return Response(self.get_formatted_timezones(), status=status.HTTP_200_OK)

    @staticmethod
    def get_formatted_timezones():
        """
        Retrieves and formats the list of all time zones recognized by pytz.

        :return: A list of strings, each representing a time zone name and its GMT offset.
        """
        formatted_timezones = [constants.LOCAL_TIME, constants.SOLOMON_TIME_ZONE]
        for tz in pytz.all_timezones:
            now = datetime.now(pytz.timezone(tz))
            # Remove continent prefix
            tz_name = tz.split('/')[-1] if '/' in tz else tz
            formatted_timezones.append(f"{tz_name} (GMT{int(now.strftime('%z')) // 100:+d}:{now.strftime('%z')[3:]})")
        return formatted_timezones


class StopwatchAPI(generics.CreateAPIView, generics.ListAPIView,
                   generics.DestroyAPIView):
    serializer_class = StopwatchSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Stopwatch.objects.none()

        full_elapsed = Case(
            When(
                status=Stopwatch.STATUS_STARTED,
                start_time__isnull=False,
                then=ExpressionWrapper(
                    F("pre_time_diff") + (Now() - F("start_time")),
                    output_field=DurationField()
                )
            ),
            When(
                status=Stopwatch.STATUS_STOPPED,
                then=F("pre_time_diff")
            ),
            default=Value(None),
            output_field=DurationField()
        )

        base_queryset = Stopwatch.objects.annotate(
            lap_count=Count("laps"),
            raw_time_diff=full_elapsed,
        ).annotate(
            time_diff_sec=Case(
                When(
                    raw_time_diff__isnull=False,
                    then=(
                        ExtractDay("raw_time_diff") * 86400 +
                        ExtractHour("raw_time_diff") * 3600 +
                        ExtractMinute("raw_time_diff") * 60 +
                        ExtractSecond("raw_time_diff")
                    )
                ),
                default=Value(None),
                output_field=IntegerField()
            )
        )
        print("Base Queryset:", base_queryset.query)
        if check_subscription(self.request):
            return base_queryset.filter(user=self.request.user)

        return base_queryset.filter(user=self.request.user)[:constants.COUNT_UNSUBSCRIBED_STOPWATCHES]

    def delete(self, request, pk=None):
        if pk:
            # Delete/reset a specific stopwatch by ID
            stopwatch = get_object_or_404(Stopwatch, pk=pk, user=request.user)
            # stopwatch.status = "notStarted"  # Or "reset" if allowed
            # stopwatch.stopped_time = None
            stopwatch.delete()
            stopwatch.laps.all().delete()
            return Response(
                {"message": f"Stopwatch {pk} has been deleted and its laps deleted."},
                status=status.HTTP_200_OK
            )

    # Bulk delete/reset all stopwatches for the user
        stopwatches = Stopwatch.objects.filter(user=request.user)
        count = 0
        for stopwatch in stopwatches:
            stopwatch.status = "notStarted"
            stopwatch.stopped_time = None
            stopwatch.save()
            stopwatch.laps.all().delete()
            count += 1

            return Response(
            {"message": f"{count} stopwatch(es) have been reset and laps deleted."},
            status=status.HTTP_200_OK
    )



class StopwatchEditAPI(generics.UpdateAPIView):
    serializer_class = StopwatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Stopwatch.objects.none()
        if check_subscription(self.request):
            return Stopwatch.objects.filter(user=self.request.user)
        return Stopwatch.objects.filter(user=self.request.user)[:constants.COUNT_UNSUBSCRIBED_STOPWATCHES]


class LapAPI(generics.CreateAPIView):
    serializer_class = LapSerializer

    def get_queryset(self):
        if check_subscription(self.request):
            return Lap.objects.all()
        else:
            return Lap.objects.all()[:constants.COUNT_UNSUBSCRIBED_LAPS]


class StopwatchLapsAPI(generics.GenericAPIView):
    serializer_class = LapSerializer

    def get_queryset(self):
        return

    def get(self, request, pk):
        # get stopwatch
        stopwatch = get_object_or_404(Stopwatch, pk=pk, user=request.user)
        laps = stopwatch.laps if \
            check_subscription(self.request) \
            else stopwatch.laps.all()[:STOPWATCH_LAPS]
        return Response(LapSerializer(laps, many=True).data)

    def delete(self, request, pk):
        stopwatch = get_object_or_404(Stopwatch, pk=pk, user=request.user)
        stopwatch.laps.all().delete()

        return Response(status=status.HTTP_200_OK)


class ReceiptViewSet(CreateModelMixin, GenericViewSet):
    serializer_class = ReceiptSerializer
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data['os'] == 'apple':
            try:
                receipt = serializer.validated_data['receipt']

                validator = AppStoreValidator(settings.APPLE_BUNDLE_ID,
                                              sandbox=settings.APPLE_SANDBOX,
                                              auto_retry_wrong_env_request=False)
                result = validator.validate(receipt=receipt,
                                            shared_secret=settings.APPLE_SHARED_SECRET,
                                            exclude_old_transactions=False)
                receipt, created = Receipt.objects.get_or_create(user=request.user)
                receipt.response = result
                receipt.save()
                expires_date = 'unknown'
                for payment in result.get('latest_receipt_info'):
                    # here put time from front
                    expires_date = datetime.fromtimestamp(int(payment.get('expires_date_ms', 0)) / 1000, tz=pytz.UTC)
                    if expires_date > datetime.now(tz=pytz.UTC):
                        receipt.payment_expires = expires_date
                        receipt.product_id = payment['product_id']
                        receipt.status = 'active'
                        receipt.save()
                        request.user.has_subscription = True
                        request.user.save()
                        return Response(data={'subscription': receipt.status,
                                              'expires_date': expires_date}, status=status.HTTP_200_OK)

                request.user.has_subscription = False
                request.user.save()
                receipt.status = 'expired'
                receipt.save()
                return Response(data={'subscription': receipt.status,
                                      'expires_date': expires_date}, status=status.HTTP_200_OK)

            except InAppPyValidationError as exc:
                # TODO change status of subscription based on error
                return Response(data={'detail': f'Purchase validation failed {exc}'},
                                status=status.HTTP_400_BAD_REQUEST)

        elif serializer.validated_data['os'] == 'android':
            print('============= android ========================')

            try:
                signature = serializer.validated_data.get('signature')
                purchase_token = signature.get('purchaseToken')
                current_product = signature.get('productId')
                verifier = GooglePlayVerifier(
                    settings.GOOGLE_BUNDLE_ID,
                    settings.GOOGLE_API_FILE,
                )
                result = verifier.verify(purchase_token, current_product, is_subscription=True)
                receipt, created = Receipt.objects.get_or_create(user=request.user)
                receipt.response = result
                receipt.save()
                expires_date = datetime.fromtimestamp(int(result.get('expiryTimeMillis', 0)) / 1000, tz=pytz.UTC)
                if expires_date > datetime.now(tz=pytz.UTC):
                    receipt.payment_expires = expires_date
                    receipt.product_id = current_product
                    receipt.status = 'active'
                    receipt.save()
                    request.user.has_subscription = True
                    request.user.save()
                    return Response(data={'subscription': receipt.status,
                                          'expires_date': expires_date}, status=status.HTTP_200_OK)
                request.user.has_subscription = False
                request.user.save()
                receipt.status = 'expired'
                receipt.save()
                return Response(data={'subscription': receipt.status,
                                      'expires_date': expires_date}, status=status.HTTP_200_OK)
            except errors.GoogleError as exc:
                print(exc, exc.raw_response, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                return Response(data={'detail': f'Purchase validation failed {exc}'},
                                status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(str(e), "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                return Response(data={'detail': f'Purchase validation failed {e}'},
                                status=status.HTTP_400_BAD_REQUEST)
    

class PublicStopwatchAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            uuid = request.GET.get("uuid")
            as_pdf = request.GET.get("pdf") == "true"
            as_image = request.GET.get("image") == "true"

            if not uuid:
                return Response(
                    {"detail": "Missing uuid parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            stopwatch = get_object_or_404(Stopwatch, public_uuid=uuid)
            serializer = StopwatchSerializer(stopwatch)

            base_path = os.path.join(settings.MEDIA_ROOT, "public", "stopwatch", str(uuid))
            os.makedirs(base_path, exist_ok=True)

            response_data = {
                "detail": "Stopwatch fetched successfully",
                "stopwatch": serializer.data,
            }

            # Generate PDF
            if as_pdf:
                pdf_template = get_template("stopwatch_pdf.html")
                html = pdf_template.render({"stopwatch": stopwatch})
                pdf_path = os.path.join(base_path, f"{uuid}.pdf")
                with open(pdf_path, "wb") as pdf_file:
                    pisa.CreatePDF(BytesIO(html.encode("utf-8")), dest=pdf_file)
                response_data["pdf_url"] = f"/media/public/stopwatch/{uuid}/{uuid}.pdf"

            # Generate Image
            if as_image:
                hti = Html2Image()
                html = get_template("stopwatch_pdf.html").render({"stopwatch": stopwatch})
                image_filename = f"{uuid}.png"
                image_path = os.path.join(base_path, image_filename)
                hti.screenshot(html_str=html, save_as=image_filename, size=(800, 600), output_path=base_path)
                response_data["image_url"] = f"/media/public/stopwatch/{uuid}/{uuid}.png"

            return Response(data=response_data, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e), "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return Response(
                data={"detail": f"Failed to fetch public stopwatch: {e}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class StopwatchActionAPI(APIView):
    """
    Unified endpoint to start, stop, or reset a stopwatch.
    Use query param: ?status=start|stop|reset
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        action = request.query_params.get('status')

        if action not in ["start", "stop", "reset"]:
            return Response({"detail": "Invalid status. Use start, stop, or reset."}, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            stopwatch = Stopwatch.objects.get(pk=pk, user=request.user)
        except Stopwatch.DoesNotExist:
            return Response({"detail": "Stopwatch not found."}, status=http_status.HTTP_404_NOT_FOUND)

        message = ""
        if action == "start":
            if stopwatch.status == "started":
                return Response({"detail": "Stopwatch already started."}, status=http_status.HTTP_400_BAD_REQUEST)

            stopwatch.status = "started"
            # stopwatch.stopped_time = None
            stopwatch.start_time = now()  # Set start time when starting
            message = "Stopwatch started"

        elif action == "stop":
            if stopwatch.status != "started":
                return Response({"detail": "Stopwatch is not running."}, status=http_status.HTTP_400_BAD_REQUEST)

            stopwatch.status = "stopped"
            stopwatch.stopped_time = timezone.now()

        # Save accumulated time
            if stopwatch.start_time:
                current_session = stopwatch.stopped_time - stopwatch.start_time
                stopwatch.pre_time_diff = (stopwatch.pre_time_diff or timedelta()) + current_session
                stopwatch.save()
                message = "Stopwatch stopped"

        elif action == "reset":
            stopwatch.status = "reset"
            stopwatch.stopped_time = None
            stopwatch.pre_time_diff = None
            stopwatch.laps.all().delete()
            stopwatch.start_time = None  # optional: also clear `start_time`
            message = "Stopwatch reset"

        stopwatch.save()

        # Emit over socket.io
        sio.emit("stopwatch_status", {
            "id": stopwatch.id,
            "status": stopwatch.status,
            "message": message
        })

        return Response({
            "id": stopwatch.id,
            "message": message,
            "status": stopwatch.status,
            "stopped_time": stopwatch.stopped_time,
        }, status=http_status.HTTP_200_OK)
