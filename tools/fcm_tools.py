import logging

from fcm_django.models import FCMDevice

from api import constants
from api.models import Task
from firebase_admin import messaging


logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages sending different types of notifications related to tasks.
    """

    def __init__(self):
        self.app_name = constants.APP_NAME

    def send_task_reminder(self, task: Task) -> None:
        """
        Sends a reminder notification for a task starting in 5 minutes.

        Args:
            task: The Task instance for which to send the reminder.
        """
        message = f"Task {task.title} is starting in {constants.REMINDER_TIME} minutes."
        self._send_notification(task, message)

    def send_task_start(self, task: Task) -> None:
        """
        Sends a notification indicating that a task has just started.

        Args:
            task: The Task instance for which to send the start notification.
        """
        message = f"Task {task.title} has just started."
        self._send_notification(task, message)

    def send_duration_exceeded_notification(self, task: Task) -> None:
        """
        Sends a notification indicating that a task has exceeded its planned duration.

        Args:
            task: The Task instance for which to send the notification.
        """
        message = f"Task {task.title} has exceeded its planned duration."
        self._send_notification(task, message)

    def _send_notification(self, task: Task, message: str) -> None:
        """
        Sends a push notification to all devices associated with the task's user.

        Args:
            task: The Task instance for which to send the notification.
            message: The message body for the notification.
        """
        try:
            devices = FCMDevice.objects.filter(user_id=task.user)
            messages = [messaging.Message(
                data={"notification_type": "task", "task_id": str(task.id)},
                notification=messaging.Notification(
                    title=self.app_name, body=message,),
                token=device.registration_id,
                apns=messaging.APNSConfig(payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default")))
            ) for device in devices
            ]
            for message in messages:
                messaging.send(message)
            logger.info(f"Send notification for task: {task.title}")
        except Exception as e:
            logger.error('Failed to send notification for task %s: %s', task.title, str(e))


fcm_notification = NotificationManager()
