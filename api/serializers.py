import datetime

from django.contrib.auth import get_user_model
from rest_framework import serializers, status

from . import constants
from messages import ErrorMessages
from rest_framework.serializers import ValidationError
from .models import User, Task, TaskCategory, DefaultAlarm, Quote, Stopwatch, Lap, Receipt

from .validators import PhoneNumberValidation
from django.utils.timezone import localtime
import pytz

UserModel = get_user_model()


class PhoneNumberSerializer(serializers.Serializer):
    phone_number = serializers.CharField(min_length=5)

    @staticmethod
    def validate_phone_number(value: str):
        return PhoneNumberValidation.validate(value)


class PhoneNumberAndCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(min_length=5)
    verification_code = serializers.CharField(min_length=constants.VERIFICATION_CODE_LENGTH,
                                              max_length=constants.VERIFICATION_CODE_LENGTH)

    @staticmethod
    def validate_phone_number(value):
        return PhoneNumberValidation.validate(value)

    @staticmethod
    def validate_verification_code(value):
        """
        Validates that the verification code contains only digits.
        """
        if not value.isdigit():
            raise serializers.ValidationError(ErrorMessages.VERIFICATION_CODE_ERROR)
        return value


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'name', 'phone_number', 'notifications_enabled', 'has_subscription', 'timezone')
        read_only_fields = ('id',)


class TaskSerializer(serializers.ModelSerializer):
    time_zone = serializers.CharField(required=True, max_length=50, min_length=2)
    done = serializers.BooleanField(default=False)

    class Meta:
        model = Task
        fields = ('id', 'title', 'description', 'longitude', 'latitude',
                  'address', 'date', 'start_time', 'end_time', 'tracked_time',
                  'send_notification', 'done', 'category', 'time_zone')
        read_only_fields = ('user',)

    def to_representation(self, instance):
        # Ensure the category field is properly serialized
        self.fields['category'] = TaskCategoriesSerializer(read_only=True)
        representation = super(TaskSerializer, self).to_representation(instance)

        # Format the tracked_time field
        if 'tracked_time' in representation and instance.tracked_time:
            # Convert it to a formatted string HH:MM:SS
            if isinstance(instance.tracked_time, datetime.timedelta):
                total_seconds = int(instance.tracked_time.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                representation['tracked_time'] = '{:02}:{:02}:{:02}'.format(hours, minutes, seconds)
            else:
                representation['tracked_time'] = '00:00:00'
        return representation


class TaskNamesListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ('id', 'title')


class TaskCategoriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = '__all__'


class DefaultAlarmSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = DefaultAlarm
        fields = '__all__'


class QuotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ('quote',)


class FCMTokenSerializer(serializers.Serializer):
    device_id = serializers.CharField()


class StopwatchSerializer(serializers.ModelSerializer):
    laps = serializers.SerializerMethodField(read_only=True)
    time_diff_sec = serializers.IntegerField(read_only=True)
    start_time_local = serializers.SerializerMethodField()
    stopped_time_local = serializers.SerializerMethodField()
    date_time_local = serializers.SerializerMethodField()

    class Meta:
        model = Stopwatch
        exclude = ('user',)

    def create(self, validated_data):
        from .views import check_subscription

        request = self.context.get('request')
        if (not check_subscription(request) and
                request.user.stopwatches.count() >= constants.COUNT_UNSUBSCRIBED_STOPWATCHES):
            raise ValidationError(
                {
                    'message': f'You can not create new stopwatch, '
                               f'because you have {constants.COUNT_UNSUBSCRIBED_STOPWATCHES} '
                               f'stopwatches and have not subscription!',
                    'type': 'subscription'
                },
                status.HTTP_400_BAD_REQUEST)

        stopwatch = Stopwatch.objects.create(user=request.user,
                                             **validated_data)

        return stopwatch

    def get_laps(self, obj):
        return obj.laps.count()
    def get_timezone(self):
        request = self.context.get("request")
        tz_str = request.headers.get("X-Timezone", "Asia/Kolkata")  # ⬅️ or get from user profile
        try:
            return pytz.timezone(tz_str)
        except Exception:
            return pytz.UTC

    def to_local(self, dt):
        if dt:
            return localtime(dt, timezone=self.get_timezone()).isoformat()
        return None

    def get_start_time_local(self, obj):
        return self.to_local(obj.start_time)

    def get_stopped_time_local(self, obj):
        return self.to_local(obj.stopped_time)

    def get_date_time_local(self, obj):
        return self.to_local(obj.date_time)


class LapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lap
        fields = '__all__'

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        user_stopwatches = user.stopwatches.all()

        if validated_data.get('stopwatch') not in user_stopwatches:
            raise ValidationError(
                {
                    'message': 'No stopwatch found with the given id!'
                },
                status.HTTP_404_NOT_FOUND)
        elif not user.has_subscription and request.user.stopwatches.count() >= 2:
            raise ValidationError(
                {
                    'message': 'You can not create lap!',
                    'type': 'subscription'
                },
                status.HTTP_404_NOT_FOUND)

        lap = Lap.objects.create(**validated_data)

        return lap


class ReceiptSerializer(serializers.ModelSerializer):
    os = serializers.ChoiceField(choices=(('apple', 'apple'), ('android', 'android')), required=True)
    receipt = serializers.CharField(required=False, help_text='Only for iOS')
    signature = serializers.JSONField(required=False, help_text='Only for android')

    class Meta:
        model = Receipt
        fields = ('os', 'receipt', 'signature')

    def validate(self, attrs):
        if attrs.get('os') == 'apple' and not attrs.get('receipt'):
            raise ValidationError('For iOS receipt is required.')
        if attrs.get('os') == 'android' and not attrs.get('signature'):
            raise ValidationError('For Android signature is required.')
        return attrs
