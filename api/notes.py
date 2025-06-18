import logging
from os import environ
from datetime import date, datetime

from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

import dramatiq  # Add this import

from .models import Notes

logger = logging.getLogger(__name__)

QUEUE_NAME = getattr(settings, "DRAMATIQ_DEFAULT_QUEUE", "redis")

job_stores = {
    QUEUE_NAME: RedisJobStore(
        jobs_key='expired_notes_jobs',
        run_times_key='expired_notes_running',
        host=environ.get("REDIS_HOST", "localhost"),
        port=int(environ.get("REDIS_PORT", 6379)),
        username=(environ.get("REDIS_USERNAME") or None),  # Use None if not set
        password=(environ.get("REDIS_PASSWORD") or None),  # Use None if not set
        db=int(environ.get("REDIS_DB", 0)),
    )
}
scheduler = BackgroundScheduler(jobstores=job_stores)

def run_scheduler():
    if not scheduler.running:
        try:
            print("Starting APScheduler...")
            scheduler.start()
            print(f"APScheduler running state: {scheduler.running}")
        except Exception as e:
            print(f"ERROR starting scheduler: {e}")
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
    else:
        print("APScheduler already running for notes.")
        return True

def mark_expired_notes():
    today = date.today()
    print(f"Marking expired notes as deleted...: {today}")
    print("Notessssssssssss------")
    logger.info(f"Marking expired notes as deleted...: {today}")
    expired_notes = Notes.objects.filter(expiry_date=today, isDelete="false")
    logger.info(f"Found {expired_notes.count()} expired notes.")
    logger.info(f"Notessssssssssss------ {expired_notes}")
    for note in expired_notes:
        note.isDelete = "true"
        note.save()
    logger.info(f"[{datetime.now()}] Marked {expired_notes.count()} expired notes as deleted.")

def schedule_expired_notes_job():
    run_scheduler()
    print(f"Scheduling expired notes job with queue: {QUEUE_NAME}")
    scheduler.add_job(
        mark_expired_notes,
        'interval',
        seconds=30,
        jobstore=QUEUE_NAME,
        id='mark_expired_notes_job',
        replace_existing=True
    )

def start():
    schedule_expired_notes_job()

# Dramatiq actor to trigger scheduling from anywhere
@dramatiq.actor(queue_name=QUEUE_NAME)
def schedule_expired_notes_actor():
    try:
        schedule_expired_notes_job()
        logger.info("Scheduled expired notes job via Dramatiq actor.")
        print("Scheduled expired notes job via Dramatiq actor.")
    except Exception as e:
        print(f"ERROR in schedule_expired_notes_actor: {e}")
        logger.error(f"Failed in schedule_expired_notes_actor: {e}", exc_info=True)
