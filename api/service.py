import logging
from api.validators import user_friendly_timezone_to_iana
from .tasks import schedule_task_notification, remove_scheduled_job, send_reminder_notification, send_start_notification

# Set up logger
logger = logging.getLogger(__name__)

class TaskUpdateService:
    def __init__(self, task, user):
        self.reschedule_notification = False
        self.task = task
        self.user = user
        self.initial_notification_setting = self.task.send_notification
        
        print(f"[DEBUG] TaskUpdateService initialized for task ID: {task.id}")
        print(f"[DEBUG] Initial notification setting: {self.initial_notification_setting}")
        logger.info(f"TaskUpdateService initialized for task {task.id}, user {user.id}")

    def update_task(self, validated_data):
        print(f"[DEBUG] Starting task update with data: {validated_data}")
        logger.info(f"Updating task {self.task.id} with data: {validated_data}")
        
        self._update_time_zone_if_needed(validated_data)
        self._check_task_attributes(validated_data)
        self._update_notifications(validated_data)
        self._update_task_model(self.task, validated_data)

        print(f"[DEBUG] Reschedule notification flag: {self.reschedule_notification}")
        logger.debug(f"Reschedule notification flag: {self.reschedule_notification}")
        
        if self.reschedule_notification:
            print("[DEBUG] Rescheduling notifications...")
            logger.info(f"Rescheduling notifications for task {self.task.id}")
            self._reschedule_notifications()
        else:
            print("[DEBUG] No notification rescheduling needed")
            logger.debug("No notification rescheduling needed")
            
        print(f"[DEBUG] Task update completed for task ID: {self.task.id}")
        logger.info(f"Task update completed for task {self.task.id}")
        return self.task

    @staticmethod
    def _update_task_model(task, validated_data):
        print(f"[DEBUG] Updating task model with: {validated_data}")
        logger.debug(f"Updating task {task.id} model with validated data")
        
        for key, value in validated_data.items():
            old_value = getattr(task, key, None)
            setattr(task, key, value)
            print(f"[DEBUG] Updated {key}: {old_value} -> {value}")
            logger.debug(f"Task {task.id}: {key} changed from {old_value} to {value}")
            
        task.save()
        print(f"[DEBUG] Task model saved successfully")
        logger.info(f"Task {task.id} model saved successfully")

    def _update_time_zone_if_needed(self, data):
        time_zone = data.get('time_zone')
        print(f"[DEBUG] Checking timezone update: current={self.task.time_zone}, new={time_zone}")
        logger.debug(f"Checking timezone update for task {self.task.id}")
        
        if time_zone and time_zone != self.task.time_zone:
            print(f"[DEBUG] Timezone change detected: {self.task.time_zone} -> {time_zone}")
            logger.info(f"Timezone change detected for task {self.task.id}: {self.task.time_zone} -> {time_zone}")
            
            iana_timezone, _ = user_friendly_timezone_to_iana(time_zone, self.user)
            data['time_zone'] = iana_timezone
            self.reschedule_notification = True
            
            print(f"[DEBUG] Converted to IANA timezone: {iana_timezone}")
            print(f"[DEBUG] Reschedule notification set to: {self.reschedule_notification}")
            logger.info(f"Converted timezone to IANA format: {iana_timezone}")
        else:
            print("[DEBUG] No timezone change needed")
            logger.debug("No timezone change needed")

    def _check_task_attributes(self, data):
        attributes_to_check = ['start_time', 'end_time', 'date']
        print(f"[DEBUG] Checking attributes for changes: {attributes_to_check}")
        logger.debug(f"Checking task {self.task.id} attributes for changes")
        
        for attr in attributes_to_check:
            new_value = data.get(attr)
            current_value = getattr(self.task, attr)
            
            print(f"[DEBUG] Checking {attr}: current={current_value}, new={new_value}")
            
            if new_value and new_value != current_value:
                print(f"[DEBUG] Attribute change detected for {attr}: {current_value} -> {new_value}")
                logger.info(f"Task {self.task.id} attribute {attr} changed: {current_value} -> {new_value}")
                self.reschedule_notification = True
                print(f"[DEBUG] Reschedule notification set to: {self.reschedule_notification}")
            else:
                print(f"[DEBUG] No change for {attr}")
                
        logger.debug(f"Attribute check completed. Reschedule flag: {self.reschedule_notification}")

    def _update_notifications(self, data):
        send_notification = data.get('send_notification')
        print(f"[DEBUG] Checking notification settings: current={self.initial_notification_setting}, new={send_notification}")
        logger.debug(f"Checking notification settings for task {self.task.id}")
        
        if send_notification is not None and send_notification != self.initial_notification_setting:
            print(f"[DEBUG] Notification setting changed: {self.initial_notification_setting} -> {send_notification}")
            logger.info(f"Notification setting changed for task {self.task.id}: {self.initial_notification_setting} -> {send_notification}")
            
            if send_notification:
                print("[DEBUG] Notifications enabled - will reschedule")
                self.reschedule_notification = True
                logger.info(f"Notifications enabled for task {self.task.id}")
            else:
                print("[DEBUG] Notifications disabled - removing scheduled notifications")
                self.reschedule_notification = False
                logger.info(f"Notifications disabled for task {self.task.id}")
                self._remove_scheduled_notifications()
                
            print(f"[DEBUG] Reschedule notification set to: {self.reschedule_notification}")
        else:
            print("[DEBUG] No notification setting change")
            logger.debug("No notification setting change")

    def _reschedule_notifications(self):
        print(f"[DEBUG] Rescheduling notifications for task ID: {self.task.id}")
        logger.info(f"Rescheduling notifications for task {self.task.id}")
        
        try:
            schedule_task_notification.send_with_options(args=(self.task.id,))
            print(f"[DEBUG] Successfully scheduled notification for task ID: {self.task.id}")
            logger.info(f"Successfully scheduled notification for task {self.task.id}")
        except Exception as e:
            print(f"[DEBUG] Error scheduling notification: {e}")
            logger.error(f"Error scheduling notification for task {self.task.id}: {e}")

    def _remove_scheduled_notifications(self):
        print(f"[DEBUG] Removing scheduled notifications for task ID: {self.task.pk}")
        logger.info(f"Removing scheduled notifications for task {self.task.pk}")
        
        try:
            # Remove reminder notification
            remove_scheduled_job.send_with_options(args=(self.task.pk, send_reminder_notification.__name__))
            print(f"[DEBUG] Removed reminder notification for task ID: {self.task.pk}")
            logger.info(f"Removed reminder notification for task {self.task.pk}")
            
            # Remove start notification
            remove_scheduled_job.send_with_options(args=(self.task.pk, send_start_notification.__name__))
            print(f"[DEBUG] Removed start notification for task ID: {self.task.pk}")
            logger.info(f"Removed start notification for task {self.task.pk}")
            
        except Exception as e:
            print(f"[DEBUG] Error removing scheduled notifications: {e}")
            logger.error(f"Error removing scheduled notifications for task {self.task.pk}: {e}")