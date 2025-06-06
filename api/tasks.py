import pytz
import logging
import datetime
import dramatiq
from os import environ

from . import constants
from .models import Task
from setinc import settings
from messages import ErrorMessages
from tools.fcm_tools import fcm_notification

from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler

job_stores = {
    'redis': RedisJobStore(jobs_key='dispatched_trips_jobs',
                           run_times_key='dispatched_trips_running',
                           host=environ.get("REDIS_HOST", "localhost"),
                           port=6379)
}
scheduler = BackgroundScheduler(jobstores=job_stores)


logger = logging.getLogger(__name__)


def run_scheduler():
    if not scheduler.running:
        try:
            scheduler.start()
        except KeyboardInterrupt:
            scheduler.shutdown()
            logger.info("Scheduler shutdown.")


def get_task(task_id):
    try:
        task = Task.objects.get(pk=task_id)
        logger.info(f"STARTED NOTIFICATION FOR USER -> {task.user.name} TASK ID -> {task.pk}")
        return task
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} does not exist.")
        return None


def get_timezone(task_timezone_str: str):
    try:
        task_timezone = pytz.timezone(task_timezone_str)
    except pytz.UnknownTimeZoneError:
        logger.error(f"Invalid timezone '{task_timezone_str}'. Falling back to server's default timezone.")
        task_timezone = pytz.timezone(settings.TIME_ZONE)
    return task_timezone


def get_task_times(task: Task) -> tuple:
    task_timezone_str = task.time_zone if task.time_zone else settings.TIME_ZONE
    task_timezone = get_timezone(task_timezone_str)
    task_datetime = datetime.datetime.combine(task.date, task.start_time)
    return task_timezone.localize(task_datetime), datetime.datetime.now(task_timezone)


@dramatiq.actor(queue_name=environ.get('DRAMATIQ_DEFAULT_QUEUE', 'redis'))
def schedule_task_notification(task_id: int):
    if not (task := get_task(task_id)):
        return

    if not task.start_time:
        logger.error(ErrorMessages.TASK_START_TIME_ERROR)
        return

    if not task.send_notification:
        return

    aware_task_datetime, now_in_task_timezone = get_task_times(task)

    if aware_task_datetime - datetime.timedelta(minutes=constants.REMINDER_TIME) <= now_in_task_timezone:
        logger.info(ErrorMessages.TASK_TIME_IS_ALREADY_PASSED.format(constants.REMINDER_TIME))
        return

    # REMINDER AND START NOTIFICATION
    run_scheduler()
    schedule_job(send_reminder_notification, task,
                 aware_task_datetime - datetime.timedelta(minutes=constants.REMINDER_TIME))
    schedule_job(send_start_notification, task, aware_task_datetime)


def send_reminder_notification(task):
    logger.info(f"Sending reminder notification for task {task.id}.")
    fcm_notification.send_task_reminder(task)


def send_start_notification(task):
    logger.info(f"Sending start notification for task {task.id}.")
    fcm_notification.send_task_start(task)


def send_task_duration_reminder_notification(task):
    logging.info(f"Sending duration reminder notification for task {task.id}.")
    fcm_notification.send_duration_exceeded_notification(task)


@dramatiq.actor(queue_name=environ.get('DRAMATIQ_DEFAULT_QUEUE', 'redis'))
def schedule_task_duration(task_id: int):
    if not (task := get_task(task_id)):
        return

    if task.start_time and task.end_time and task.date:
        planned_start_datetime = datetime.datetime.combine(task.date, task.start_time)
        planned_end_datetime = datetime.datetime.combine(task.date, task.end_time)
        planned_duration = planned_end_datetime - planned_start_datetime
        planned_seconds = planned_duration.total_seconds()

        # Check if running for more than an hour and exceeded planned duration
        if planned_seconds <= constants.REMINDER_DURATION_TIME:
            _, now_in_task_timezone = get_task_times(task)
            run_scheduler()
            schedule_job(send_task_duration_reminder_notification, task, now_in_task_timezone +
                         datetime.timedelta(seconds=constants.REMINDER_DURATION_TIME))
    else:
        logger.error(f"Scheduler task duration for {task_id} not created")
        return


@dramatiq.actor(queue_name=environ.get('DRAMATIQ_DEFAULT_QUEUE', 'redis'))
def remove_scheduled_job(task_id: int, func_name: str):
    """
    Remove a scheduled job for a given task and function.

    Args:
        task_id (int): The ID of the task for which to remove the job.
        func_name: Callable which takes func
    """
    job_id = f"{task_id}_{func_name}"
    try:
        run_scheduler()
        scheduler.remove_job(job_id, jobstore='redis')
        logger.info(f"Removed scheduled job {job_id} for task {task_id}.")
    except JobLookupError as e:
        logger.error(f"Job not found: {job_id} for task {task_id}. Error message: {e}")
    except Exception as e:
        logger.error(f"Error removing job: {job_id} for task {task_id}. Error message: {e}")


def schedule_job(func, task, run_date):
    scheduler.add_job(
        func,
        'date',
        id=f"{task.id}_{func.__name__}",
        replace_existing=True,
        run_date=run_date,
        args=[task],
        jobstore='redis'
    )
    logger.info(f"Scheduled {func.__name__} for task {task.id} at {run_date}.")
