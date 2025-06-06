from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser
from phonenumber_field.modelfields import PhoneNumberField

from . import constants
from datetime import timedelta
from django.utils import timezone
from .managers import CustomUserManager
from django.core.validators import MinLengthValidator
from django.core.validators import MaxValueValidator, MinValueValidator


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = PhoneNumberField(unique=True)
    name = models.CharField(max_length=30)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    notifications_enabled = models.BooleanField(default=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    has_subscription = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return str(self.phone_number)


class VerificationCode(models.Model):
    phone_number = PhoneNumberField()
    verification_code = models.CharField(max_length=4)
    verified = models.BooleanField(default=False)

    def __str__(self):
        if self.verified:
            return str(self.phone_number) + str(' Verified')
        return str(self.phone_number) + str(' Unverified')


class TemporaryBlockedPhoneNumber(models.Model):
    phone_number = PhoneNumberField()
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return str(self.phone_number)


class TaskCategory(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural = "Task Categories"


class Task(models.Model):
    title = models.CharField(validators=[MinLengthValidator(2)], max_length=100)
    description = models.CharField(validators=[MinLengthValidator(2)], max_length=1000)
    longitude = models.DecimalField(max_digits=20, decimal_places=16,
                                    null=True, blank=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=16, null=True,
                                   blank=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    tracked_time = models.DurationField(blank=True, default=timedelta)
    send_notification = models.BooleanField(default=False)
    time_zone = models.CharField(max_length=50, default=constants.DEFAULT_TIME_ZONE)
    done = models.BooleanField(default=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='tasks')
    category = models.ForeignKey(TaskCategory, null=True,
                                 on_delete=models.SET_NULL)
    start_tracked_time = models.DateTimeField(null=True, blank=True, help_text="The time when the task was started.")

    def __str__(self):
        return str(self.title)


class Alarm(models.Model):
    time_zone = models.CharField(max_length=50)
    time = models.TimeField()
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)
    sound_name = models.CharField(max_length=50)
    sound_level = models.PositiveIntegerField(
        default=50,
        validators=[
            MaxValueValidator(100),
            MinValueValidator(0)
        ]
    )
    snooze = models.BooleanField(default=False)
    vibration = models.BooleanField(default=False)
    label = models.CharField(max_length=50, null=True)
    active = models.BooleanField(default=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alarms')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Alarm for {self.user.phone_number} at {self.time}"


class DefaultAlarm(models.Model):
    sound_name = models.CharField(max_length=50)
    sound_level = models.PositiveIntegerField(
        default=50,
        validators=[
            MaxValueValidator(100),
            MinValueValidator(0)
        ]
    )
    snooze = models.BooleanField(default=False)
    vibration = models.BooleanField(default=False)

    user = models.OneToOneField(User, on_delete=models.CASCADE)


class Stopwatch(models.Model):
    label = models.CharField(max_length=50)
    date_time = models.DateTimeField(auto_now_add=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=16,
                                    null=True, blank=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=16, null=True,
                                   blank=True)
    address = models.CharField(max_length=200, blank=True, null=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='stopwatches')

    class Meta:
        verbose_name_plural = "Stopwatches"


class Lap(models.Model):
    name = models.CharField(max_length=50)
    duration = models.DurationField()

    stopwatch = models.ForeignKey(Stopwatch, on_delete=models.CASCADE,
                                  related_name='laps')


class Quote(models.Model):
    quote = models.TextField()

    def __str__(self):
        return self.quote


class Receipt(models.Model):
    STATUS_CHOICES = (
        ('active', 'active'),
        ('expired', 'expired'),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=False, blank=False)
    product_id = models.CharField(max_length=100, null=True, blank=True)  # TODO change to choice field
    response = models.TextField(null=True, blank=True)
    payment_expires = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f'{self.user.name}'
