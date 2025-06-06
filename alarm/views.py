from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from api import constants
from api.models import Alarm
from messages import ErrorMessages
from .permissions import IsAlarmOwner
from .serializers import AlarmSerializer
from api.views import check_subscription
from api.validators import user_friendly_timezone_to_iana


class AlarmViewSet(viewsets.ModelViewSet):
    serializer_class = AlarmSerializer
    permission_classes = [IsAuthenticated, IsAlarmOwner]
    queryset = Alarm.objects.all()
    tags = ["Alarm"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Alarm.objects.none()
        return Alarm.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Apply conditional slicing here instead of get_queryset
        if not check_subscription(request):
            queryset = queryset[:constants.COUNT_UNSUBSCRIBED_ALARM]

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        task = serializer.validated_data.get('task', None)
        if task and task.user != self.request.user:
            return Response(ErrorMessages.TASK_NOT_YOURS, status=status.HTTP_403_FORBIDDEN)

        if (not check_subscription(self.request) and self.request.user.alarms.filter(
                active=True).count() >= constants.COUNT_UNSUBSCRIBED_ALARM):
            raise ValidationError(
                {
                    'message': f'You can not create new alarm, '
                               f'because you have {constants.COUNT_UNSUBSCRIBED_ALARM} '
                               f'alarms and have not subscription!',
                    'type': 'subscription'
                },
                status.HTTP_400_BAD_REQUEST)
        self.handle_time_zone(serializer)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        alarm = get_object_or_404(Alarm, id=self.kwargs.get('pk'), user=self.request.user)
        # Check if 'time_zone' is in the incoming request and has changed
        incoming_time_zone = serializer.validated_data.get('time_zone', None)
        if incoming_time_zone and incoming_time_zone != alarm.time_zone:
            self.handle_time_zone(serializer)
        serializer.save()

    def handle_time_zone(self, serializer):
        """Handles the conversion of a user-friendly time zone to an IANA time zone."""
        if time_zone := serializer.validated_data.get('time_zone', None):
            time_zone_nice, time_zone = user_friendly_timezone_to_iana(time_zone, self.request.user)
            serializer.validated_data['time_zone'] = time_zone
            # serializer.validated_data['time_zone_nice'] = time_zone_nice
