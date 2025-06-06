import re
import pytz
import phonenumbers
from datetime import datetime, time

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

import api.constants
from api import constants
from messages import ErrorMessages
from task.timezone_mappings import TIMEZONES_MAPPING


class PhoneNumberValidation:
    """
    A class to encapsulate phone number validation logic.
    """

    @staticmethod
    def validate(value: str) -> str:
        if value.startswith(constants.SOLOMON_ISLAND_CODE):
            return PhoneNumberValidation._validate_solomon_islands(value)
        else:
            return PhoneNumberValidation._validate_with_phone_number_lib(value)

    @staticmethod
    def _validate_solomon_islands(value: str) -> str:
        """
        Validate Solomon Islands phone numbers.
        """
        solomon_islands_phone_regex = r"^\+677\d{5,7}$"
        if not re.match(solomon_islands_phone_regex, value):
            raise serializers.ValidationError(ErrorMessages.WRONG_PHONE_NUMBER_FORMAT)
        return value

    @staticmethod
    def _validate_with_phone_number_lib(value: str) -> str:
        """
        Validate phone numbers using the phonenumbers library.
        """
        try:
            phone_number_obj = phonenumbers.parse(value)
            if not phonenumbers.is_valid_number(phone_number_obj):
                raise serializers.ValidationError(ErrorMessages.WRONG_PHONE_NUMBER_FORMAT)
        except phonenumbers.NumberParseException:
            raise serializers.ValidationError(ErrorMessages.WRONG_PHONE_NUMBER_FORMAT)
        return value


def adjust_hour_in_timezone_description(description: str, adjustment: int) -> str:
    """
    Adjusts the hour in the timezone description.

    Parameters:
    - description (str): The timezone description, e.g., "Toronto (GMT-5:00)"
    - adjustment (int): The number of hours to adjust, can be positive or negative

    Returns:
    - str: The adjusted timezone description
    """
    pattern = r"(GMT[+-])(\d+):(\d\d)"
    match = re.search(pattern, description)
    if not match:
        return description  # Return original if pattern does not match

    sign, hours, minutes = match.groups()
    new_hour = int(hours) + adjustment
    # Adjust the sign if necessary
    if new_hour < 0:
        sign = 'GMT-' if sign == 'GMT+' else 'GMT+'
        new_hour = abs(new_hour)
    adjusted_description = re.sub(pattern, f"{sign}{new_hour}:{minutes}", description)
    return adjusted_description


def user_friendly_timezone_to_iana(user_friendly_timezone: str, user) -> tuple:
    """
    Converts a user-friendly timezone string to an IANA timezone string.

    This function takes a user-friendly timezone description (e.g., "New York (GMT-5)") and
    converts it to its corresponding IANA timezone format (e.g., "America/New_York").
    If the user-friendly timezone is set to a special value indicating the local time,
    it returns the user's stored timezone. This function relies on a predefined mapping (`TIMEZONES_MAPPING`)
    to convert the user-friendly timezone to IANA format.
    If the provided user-friendly timezone is not found in the mapping, a ValueError is raised.

    Parameters:
    - user_friendly_timezone (str): The user-friendly timezone string to be converted.
    - user: The user object

    Returns:
    - tuple: The IANA timezone string corresponding to the given user-friendly timezone.

    Raises:
    - ValueError: If the user-friendly timezone does not match any entry in the predefined mapping.

    """
    if user_friendly_timezone == api.constants.LOCAL_TIME:
        return user.timezone, user_friendly_timezone
    elif user_friendly_timezone in TIMEZONES_MAPPING:
        return TIMEZONES_MAPPING[user_friendly_timezone], user_friendly_timezone
    else:
        # Try adjusting the hour by +1 and -1 and search again
        for adjustment in (-1, +1):
            adjusted_timezone = adjust_hour_in_timezone_description(user_friendly_timezone, adjustment)
            if adjusted_timezone in TIMEZONES_MAPPING:
                return TIMEZONES_MAPPING[adjusted_timezone], adjusted_timezone
        raise ValidationError({"time_zone": f"Timezone not found: {user_friendly_timezone}"})


def validate_date_and_time(time_zone: str, date: datetime.date,
                           start_time: datetime.time = None,
                           end_time: datetime.time = None) -> None:
    """
    Validates that the given date is not in the past for the specified timezone,
    and if both start_time and end_time are provided, ensures that end_time is
    after start_time.

    Args:
        time_zone: A string representing the timezone.
        date: The date to validate.
        start_time (optional): The start time to validate.
        end_time (optional): The end time to validate.

    Raises:
        ValidationError: If the date is in the past, or end_time is not greater than start_time.
    """
    tz = pytz.timezone(time_zone)
    now = timezone.now().astimezone(tz) if start_time else timezone.now().astimezone(tz).replace(hour=00, minute=00,
                                                                                                 second=00,
                                                                                                 microsecond=00)
    # Convert the given date and times into timezone-aware datetime objects for comparison
    date_start = datetime.combine(date, start_time if start_time else time.min, tzinfo=tz)
    date_end = datetime.combine(date, end_time if end_time else time.max, tzinfo=tz)

    # Check if the date (and optionally time) is in the past
    if date_start < now:
        raise ValidationError({"error": ErrorMessages.DATE_IN_PAST})

    # If both start_time and end_time are provided, ensure end_time is after start_time
    if start_time and end_time and date_end <= date_start:
        raise ValidationError({"error": ErrorMessages.END_TIME_BEFORE_START_TIME})
