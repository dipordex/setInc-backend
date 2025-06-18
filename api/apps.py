from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)

class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        # Only run scheduler in the main process, not in reload cycles or worker processes
        if os.environ.get('RUN_MAIN', None) != 'true':
            try:
                # Firebase setup
                import firebase_admin
                from django.conf import settings
                credentials = firebase_admin.credentials.Certificate(settings.FIREBASE_PATH)
                firebase_admin.initialize_app(credentials)
                
                # Notes scheduler 
                from .notes import schedule_expired_notes_actor, run_scheduler as run_notes_scheduler
                run_notes_scheduler()
                print("Notes scheduler initialized")
                schedule_expired_notes_actor()
                
                # Tasks scheduler (your new test)
                from .tasks import run_scheduler as run_tasks_scheduler
                run_tasks_scheduler()
                print("Tasks scheduler initialized")
                
            except Exception as e:
                print(f"ERROR in ApiConfig.ready(): {e}")
                logger.exception("Failed to initialize scheduler")
