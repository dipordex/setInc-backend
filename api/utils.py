import datetime

from django.db import models
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()


def user_soft_delete(user: User) -> None:
    """
    Soft deletes a user by deactivating the user and deleting all related records except for 'Receipt'.

    This function sets the user's 'is_active' field to False to indicate that the user is deactivated.
    It also deletes all related objects, except for those associated with the 'Receipt' model.

    Args: user (User): The user to be soft deleted.
    Returns: None
    """

    # Loop through all related objects
    for related_object in user._meta.related_objects:
        related_manager = getattr(user, related_object.get_accessor_name(), None)

        if not related_manager:
            continue

        if isinstance(related_manager, models.Manager):
            # Handle one-to-many or many-to-many relationships
            related_manager.all().delete()
        else:
            # Handle one-to-one relationships, skip 'receipt'
            if related_object.name != 'receipt' and hasattr(related_manager, 'delete'):
                related_manager.delete()

    # Set user to inactive after related objects are processed
    user.is_active = False
    user.save()


def get_token_for_user(user):
    access_token = str(AccessToken.for_user(user))
    refresh_token = str(RefreshToken.for_user(user))

    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }


def beautify_duration(duration):
    if duration:
        days, seconds = duration.days, duration.seconds
        hours = days * 24 + seconds // 3600
        minutes = (seconds % 3600) // 60
        return '{}h:{}m'.format(hours, minutes)
    return ''


def get_start_of_week(date: datetime, start_of_week: int = 0) -> datetime:
    """
    Calculate the start date of the week for a given date.

    Parameters:
    - date (datetime): The reference date from which to calculate the start of the week.
    - start_of_week (int): The weekday to consider as the start of the week (0 for Monday, 6 for Sunday).

    Returns:
    - datetime: The start date of the week.
    """
    weekday = date.weekday()
    start_date = date - datetime.timedelta(days=weekday - start_of_week)
    return start_date
