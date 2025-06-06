from api.validators import user_friendly_timezone_to_iana
from .tasks import schedule_task_notification, remove_scheduled_job, send_reminder_notification, send_start_notification


class TaskUpdateService:
    def __init__(self, task, user):
        self.reschedule_notification = False
        self.task = task
        self.user = user
        self.initial_notification_setting = self.task.send_notification

    def update_task(self, validated_data):
        self._update_time_zone_if_needed(validated_data)
        self._check_task_attributes(validated_data)
        self._update_notifications(validated_data)
        self._update_task_model(self.task, validated_data)

        if self.reschedule_notification:
            self._reschedule_notifications()
        return self.task

    @staticmethod
    def _update_task_model(task, validated_data):
        for key, value in validated_data.items():
            setattr(task, key, value)
        task.save()

    def _update_time_zone_if_needed(self, data):
        time_zone = data.get('time_zone')
        if time_zone and time_zone != self.task.time_zone:
            iana_timezone, _ = user_friendly_timezone_to_iana(time_zone, self.user)
            data['time_zone'] = iana_timezone
            self.reschedule_notification = True

    def _check_task_attributes(self, data):
        attributes_to_check = ['start_time', 'end_time', 'date']
        for attr in attributes_to_check:
            if data.get(attr) and data[attr] != getattr(self.task, attr):
                self.reschedule_notification = True

    def _update_notifications(self, data):
        send_notification = data.get('send_notification')
        if send_notification is not None and send_notification != self.initial_notification_setting:
            if send_notification:
                self.reschedule_notification = True
            else:
                self.reschedule_notification = False
                self._remove_scheduled_notifications()

    def _reschedule_notifications(self):
        schedule_task_notification.send_with_options(args=(self.task.id,))

    def _remove_scheduled_notifications(self):
        remove_scheduled_job.send_with_options(args=(self.task.pk, send_reminder_notification.__name__))
        remove_scheduled_job.send_with_options(args=(self.task.pk, send_start_notification.__name__))
