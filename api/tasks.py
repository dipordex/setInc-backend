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

print("DEBUG: Initializing task scheduler module")

job_stores = {
    'redis': RedisJobStore(jobs_key='dispatched_trips_jobs',
                           run_times_key='dispatched_trips_running',
                           host=environ.get("REDIS_HOST", "localhost"),
                           port=int(environ.get("REDIS_PORT", 6379)),
                           username=environ.get("REDIS_USERNAME", 'hir'),
                           password=environ.get("REDIS_PASSWORD", 'Ordex@123'),
                           db=int(environ.get("REDIS_DB", 0))
                           )
}

print(f"DEBUG: Redis job store configured - Host: {environ.get('REDIS_HOST', 'localhost')}, Port: {environ.get('REDIS_PORT', 6379)}")

scheduler = BackgroundScheduler(jobstores=job_stores)
logger = logging.getLogger(__name__)

print("DEBUG: Background scheduler initialized")


def run_scheduler():
    print(f"DEBUG: run_scheduler() called - Current scheduler state: {scheduler.running}")
    if not scheduler.running:
        try:
            print("Starting APScheduler IN TASKS... for tasks.")
            scheduler.start()
            print(f"APScheduler running state: {scheduler.running}")
            print("DEBUG: Scheduler started successfully")
        except KeyboardInterrupt:
            print("KeyboardInterrupt received, shutting down scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shutdown.")
            print("DEBUG: Scheduler shutdown due to KeyboardInterrupt")
        except Exception as e:
            print(f"DEBUG: Error starting scheduler: {e}")
    else:
        print("DEBUG: Scheduler is already running")


def get_task(task_id):
    print(f"DEBUG: get_task() called with task_id: {task_id}")
    try:
        task = Task.objects.get(pk=task_id)
        logger.info(f"STARTED NOTIFICATION FOR USER -> {task.user.name} TASK ID -> {task.pk}")
        print(f"STARTED NOTIFICATION FOR USER IN TASKS -> {task}")
        print(f"DEBUG: Task found - ID: {task.pk}, User: {task.user.name}")
        return task
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} does not exist.")
        print(f"DEBUG: Task with id {task_id} does not exist")
        return None
    except Exception as e:
        print(f"DEBUG: Error retrieving task {task_id}: {e}")
        return None


def get_timezone(task_timezone_str: str):
    print(f"DEBUG: get_timezone() called with timezone: {task_timezone_str}")
    try:
        task_timezone = pytz.timezone(task_timezone_str)
        print(f"Task timezone set to {task_timezone_str}.")
        print(f"DEBUG: Timezone successfully set to {task_timezone_str}")
    except pytz.UnknownTimeZoneError:
        logger.error(f"Invalid timezone '{task_timezone_str}'. Falling back to server's default timezone.")
        print(f"DEBUG: Invalid timezone '{task_timezone_str}', falling back to {settings.TIME_ZONE}")
        task_timezone = pytz.timezone(settings.TIME_ZONE)
    except Exception as e:
        print(f"DEBUG: Error setting timezone: {e}")
        task_timezone = pytz.timezone(settings.TIME_ZONE)
    return task_timezone


def get_task_times(task: Task) -> tuple:
    print(f"DEBUG: get_task_times() called for task {task.pk}")
    task_timezone_str = task.time_zone if task.time_zone else settings.TIME_ZONE
    print(f"DEBUG: Using timezone: {task_timezone_str}")
    
    task_timezone = get_timezone(task_timezone_str)
    task_datetime = datetime.datetime.combine(task.date, task.start_time)
    print("TASKS IN get_task_times........")
    print(f"DEBUG: Task datetime: {task_datetime}")
    
    aware_task_datetime = task_timezone.localize(task_datetime)
    now_in_task_timezone = datetime.datetime.now(task_timezone)
    
    print(f"DEBUG: Aware task datetime: {aware_task_datetime}")
    print(f"DEBUG: Current time in task timezone: {now_in_task_timezone}")
    
    return aware_task_datetime, now_in_task_timezone


@dramatiq.actor(queue_name=environ.get('DRAMATIQ_DEFAULT_QUEUE', 'redis'))
def schedule_task_notification(task_id: int):
    print(f"DEBUG: schedule_task_notification() called for task_id: {task_id}")
    print(f"Scheduling task notification for task ID: {task_id}")
    
    if not (task := get_task(task_id)):
        print(f"Task with ID {task_id} not found.")
        print(f"DEBUG: Exiting schedule_task_notification - task not found")
        return

    print(f"DEBUG: Task found - checking start_time: {task.start_time}")
    if not task.start_time:
        logger.error(ErrorMessages.TASK_START_TIME_ERROR)
        print("DEBUG: Task start time is missing")
        return

    print(f"DEBUG: Task send_notification setting: {task.send_notification}")
    if not task.send_notification:
        print("DEBUG: Task notifications disabled, exiting")
        return

    aware_task_datetime, now_in_task_timezone = get_task_times(task)
    reminder_time = aware_task_datetime - datetime.timedelta(minutes=constants.REMINDER_TIME)
    
    print(f"DEBUG: Reminder time calculated: {reminder_time}")
    print(f"DEBUG: Current time: {now_in_task_timezone}")
    print(f"DEBUG: Reminder time comparison: {reminder_time <= now_in_task_timezone}")

    if reminder_time <= now_in_task_timezone:
        logger.info(ErrorMessages.TASK_TIME_IS_ALREADY_PASSED.format(constants.REMINDER_TIME))
        print(f"DEBUG: Task time has already passed, cannot schedule reminder")
        return

    # REMINDER AND START NOTIFICATION
    print("DEBUG: Starting scheduler and scheduling jobs")
    run_scheduler()
    
    print("DEBUG: Scheduling reminder notification")
    schedule_job(send_reminder_notification, task, reminder_time)
    
    print("DEBUG: Scheduling start notification")
    schedule_job(send_start_notification, task, aware_task_datetime)
    
    print("DEBUG: schedule_task_notification() completed successfully")


def send_reminder_notification(task):
    print(f"DEBUG: send_reminder_notification() called for task {task.id}")
    logger.info(f"Sending reminder notification for task {task.id}.")
    try:
        fcm_notification.send_task_reminder(task)
        print(f"DEBUG: Reminder notification sent successfully for task {task.id}")
    except Exception as e:
        print(f"DEBUG: Error sending reminder notification for task {task.id}: {e}")


def send_start_notification(task):
    print(f"DEBUG: send_start_notification() called for task {task.id}")
    logger.info(f"Sending start notification for task {task.id}.")
    try:
        fcm_notification.send_task_start(task)
        print(f"DEBUG: Start notification sent successfully for task {task.id}")
    except Exception as e:
        print(f"DEBUG: Error sending start notification for task {task.id}: {e}")


def send_task_duration_reminder_notification(task):
    print(f"DEBUG: send_task_duration_reminder_notification() called for task {task.id}")
    logging.info(f"Sending duration reminder notification for task {task.id}.")
    try:
        fcm_notification.send_duration_exceeded_notification(task)
        print(f"DEBUG: Duration reminder notification sent successfully for task {task.id}")
    except Exception as e:
        print(f"DEBUG: Error sending duration reminder notification for task {task.id}: {e}")


@dramatiq.actor(queue_name=environ.get('DRAMATIQ_DEFAULT_QUEUE', 'redis'))
def schedule_task_duration(task_id: int):
    print(f"DEBUG: schedule_task_duration() called for task_id: {task_id}")
    
    if not (task := get_task(task_id)):
        print(f"DEBUG: Task {task_id} not found, exiting schedule_task_duration")
        return

    print(f"DEBUG: Task times - start: {task.start_time}, end: {task.end_time}, date: {task.date}")
    
    if task.start_time and task.end_time and task.date:
        planned_start_datetime = datetime.datetime.combine(task.date, task.start_time)
        planned_end_datetime = datetime.datetime.combine(task.date, task.end_time)
        planned_duration = planned_end_datetime - planned_start_datetime
        planned_seconds = planned_duration.total_seconds()
        
        print(f"DEBUG: Planned duration: {planned_duration} ({planned_seconds} seconds)")
        print(f"DEBUG: Reminder duration threshold: {constants.REMINDER_DURATION_TIME} seconds")

        # Check if running for more than an hour and exceeded planned duration
        if planned_seconds <= constants.REMINDER_DURATION_TIME:
            print("DEBUG: Task duration is within threshold, scheduling duration reminder")
            _, now_in_task_timezone = get_task_times(task)
            reminder_time = now_in_task_timezone + datetime.timedelta(seconds=constants.REMINDER_DURATION_TIME)
            print(f"DEBUG: Duration reminder scheduled for: {reminder_time}")
            
            run_scheduler()
            schedule_job(send_task_duration_reminder_notification, task, reminder_time)
            print("DEBUG: Duration reminder job scheduled successfully")
        else:
            print("DEBUG: Task duration exceeds threshold, no reminder needed")
    else:
        logger.error(f"Scheduler task duration for {task_id} not created")
        print(f"DEBUG: Missing required time fields for task {task_id}")
        return


@dramatiq.actor(queue_name=environ.get('DRAMATIQ_DEFAULT_QUEUE', 'redis'))
def remove_scheduled_job(task_id: int, func_name: str):
    job_id = f"{task_id}_{func_name}"
    print(f"DEBUG: remove_scheduled_job() called - job_id: {job_id}")
    
    try:
        run_scheduler()
        job = scheduler.get_job(job_id, jobstore='redis')
        print(f"DEBUG: Job lookup result: {job}")
        
        if not job:
            logger.warning(f"No job found with ID: {job_id}. Cannot remove.")
            print(f"DEBUG: No job found with ID {job_id}")
            return
            
        scheduler.remove_job(job_id, jobstore='redis')
        logger.info(f"Removed scheduled job {job_id} for task {task_id}.")
        print(f"DEBUG: Successfully removed job {job_id}")
        
    except Exception as e:
        logger.error(f"Error removing job: {job_id} for task {task_id}. Error message: {e}")
        print(f"DEBUG: Error removing job {job_id}: {e}")


def schedule_job(func, task, run_date):
    job_id = f"{task.id}_{func.__name__}"
    print(f"DEBUG: schedule_job() called - job_id: {job_id}, run_date: {run_date}")
    print(f"Scheduling job: {job_id} at {run_date}")
    
    try:
        scheduler.add_job(
            func,
            'date',
            id=job_id,
            replace_existing=True,
            run_date=run_date,
            args=[task],
            jobstore='redis'
        )
        logger.info(f"Scheduled {func.__name__} for task {task.id} at {run_date}.")
        print(f"Scheduled {func.__name__} for task {task.id} at {run_date}.")
        print(f"DEBUG: Job {job_id} scheduled successfully")
        
        # Verify job was added
        job = scheduler.get_job(job_id, jobstore='redis')
        if job:
            print(f"DEBUG: Job verification successful - {job_id} exists in scheduler")
        else:
            print(f"DEBUG: Job verification failed - {job_id} not found in scheduler")
            
    except Exception as e:
        print(f"DEBUG: Error scheduling job {job_id}: {e}")
        logger.error(f"Error scheduling job {job_id}: {e}")

print("DEBUG: Task scheduler module loaded successfully")