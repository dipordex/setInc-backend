import logging
import json
from os import environ
import requests

from google.oauth2 import service_account
import google.auth.transport.requests

from fcm_django.models import FCMDevice
from api import constants
from api.models import Task

logger = logging.getLogger(__name__)
print("DEBUG: FCM Notification Manager module loaded")


def get_firebase_access_token():
    print("DEBUG: get_firebase_access_token() called")

    credentials = service_account.Credentials.from_service_account_file(
        "firebase.json",  # 🔁 Replace with your actual path
        scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    print(f"DEBUG: Firebase access token obtained: {credentials.token}")

    return credentials.token


class NotificationManager:
    def __init__(self):
        self.app_name = constants.APP_NAME
        self.project_id = constants.PROJECT_ID
        print(f"DEBUG: Project ID set to: {self.project_id}")
        print(f"DEBUG: NotificationManager initialized with app_name: {self.app_name}")
        logger.info(f"NotificationManager initialized with app_name: {self.app_name}")

    def send_task_reminder(self, task: Task) -> None:
        print(f"DEBUG: send_task_reminder() called for task {task.id} - {task.title}")
        logger.info(f"Sending task reminder for task {task.id}: {task.title}")

        try:
            message = f"Task {task.title} is starting in {constants.REMINDER_TIME} minutes."
            print(f"DEBUG: Reminder message created: {message}")
            self._send_notification(task, message, "reminder")
        except Exception as e:
            print(f"DEBUG: Error in send_task_reminder() for task {task.id}: {e}")
            logger.error(f"Error in send_task_reminder() for task {task.id}: {e}")

    def send_task_start(self, task: Task) -> None:
        print(f"DEBUG: send_task_start() called for task {task.id} - {task.title}")
        logger.info(f"Sending task start notification for task {task.id}: {task.title}")

        try:
            message = f"Task {task.title} has just started."
            print(f"DEBUG: Start message created: {message}")
            self._send_notification(task, message, "start")
        except Exception as e:
            print(f"DEBUG: Error in send_task_start() for task {task.id}: {e}")
            logger.error(f"Error in send_task_start() for task {task.id}: {e}")

    def send_duration_exceeded_notification(self, task: Task) -> None:
        print(f"DEBUG: send_duration_exceeded_notification() called for task {task.id} - {task.title}")
        logger.info(f"Sending duration exceeded notification for task {task.id}: {task.title}")

        try:
            message = f"Task {task.title} has exceeded its planned duration."
            print(f"DEBUG: Duration exceeded message created: {message}")
            self._send_notification(task, message, "duration_exceeded")
        except Exception as e:
            print(f"DEBUG: Error in send_duration_exceeded_notification() for task {task.id}: {e}")
            logger.error(f"Error in send_duration_exceeded_notification() for task {task.id}: {e}")

    def _send_notification(self, task: Task, message: str, notification_type: str = "general") -> None:
        print(f"DEBUG: _send_notification() called for task {task.id}, type: {notification_type}")
        logger.info(f"Sending {notification_type} notification for task {task.id} to user {task.user.id}")

        try:
            devices = FCMDevice.objects.filter(user_id=task.user)
            device_count = devices.count()
            print(f"DEBUG: Found {device_count} devices for user {task.user.id}")

            if device_count == 0:
                logger.warning(f"No FCM devices found for user {task.user.id}, cannot send notification")
                return

            access_token = get_firebase_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; UTF-8"
            }

            success = 0
            failure = 0
            print(f"DEBUG: Creating FCM messages for {device_count} devices")
            for i, device in enumerate(devices):
                if not device.registration_id:
                    continue
                print(f"DEBUG: Preparing message for device token {device.registration_id}")
                payload = {
                    "message": {
                        "token": device.registration_id,
                        "notification": {
                            "title": self.app_name + task.title,
                            "body": notification_type + message 
                        },
                    }
                }

                url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
                try:
                    print(f"DEBUG: Sending notification to device {device.id}")
                    response = requests.post(url, headers=headers, data=json.dumps(payload))
                    print(f"DEBUG: FCM Response {i+1}: {response.status_code} - {response.text}")

                    if response.status_code == 200:
                        logger.debug(f"FCM message sent to device {device.id}")
                        success += 1
                    else:
                        logger.error(f"Failed to send FCM to device {device.id}: {response.text}")
                        failure += 1

                except Exception as e:
                    print(f"DEBUG: Exception for device {device.id}: {e}")
                    logger.error(f"Exception sending FCM to device {device.id}: {e}")
                    failure += 1

            print(f"DEBUG: Completed - Sent: {success}, Failed: {failure}")
            if success:
                logger.info(f"Successfully sent {success} {notification_type} notifications for task {task.id}")
            else:
                logger.error(f"Failed to send any notifications for task {task.id}")

        except Exception as e:
            print(f"DEBUG: Critical error in _send_notification: {e}")
            logger.error(f"Critical error in _send_notification for task {task.id}: {e}")


print("DEBUG: Creating NotificationManager instance")
fcm_notification = NotificationManager()
print("DEBUG: FCM notification manager instance created successfully")
logger.info("FCM notification manager initialized")
