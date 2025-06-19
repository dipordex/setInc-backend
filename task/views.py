import logging

from rest_framework import status
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from messages import SuccessMessages, ErrorMessages
from django.core.exceptions import MultipleObjectsReturned

from api.models import Task
from .permissions import IsTaskOwner
from .serializers import TaskTrackedTimeSerializer
from api.tasks import schedule_task_duration, remove_scheduled_job, send_task_duration_reminder_notification
from socket_instance import sio
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

print("DEBUG: Task tracking views module loaded")


class TaskTrackedTimeDetailView(APIView):
    """
    Retrieve the tracked time details for a specific task.
    """
    tags = ['Tasks']

    def get_object(self):
        print(f"DEBUG: get_object() called for user: {self.request.user.id if self.request.user else 'Anonymous'}")
        
        try:
            task = Task.objects.filter(user=self.request.user).first()
            print(f"DEBUG: Query result - task found: {task.id if task else 'None'}")
            
            if task:
                print(f"DEBUG: Active task details - ID: {task.id}, start_tracked_time: {task.start_tracked_time}")
                logger.info(f"Active tracking task found for user {self.request.user.id}: Task ID {task.id}")
            else:
                print(f"DEBUG: No active tracking task found for user {self.request.user.id}")
                logger.info(f"No active tracking task found for user {self.request.user.id}")
                
            return task
            
        except Exception as e:
            print(f"DEBUG: Error in get_object(): {e}")
            logger.error(f"Error retrieving active task for user {self.request.user.id}: {e}")
            return None
        
    @swagger_auto_schema(tags=['Tasks'], operation_description="Method to get tracked time")
    def get(self, request):
        """
        Retrieve and return the tracked time for the specified task.
        """
        print(f"DEBUG: TaskTrackedTimeDetailView GET request from user: {request.user.id}")
        logger.info(f"GET tracked time request from user: {request.user.id}")
        
        try:
            task = self.get_object()
            print(f"DEBUG: Retrieved task: {task.id if task else 'None'}")
            
            if not task:
                print("DEBUG: No active tracked task found, returning 404")
                logger.warning(f"No active tracked task found for user {request.user.id}")
                return Response({"error": "No active tracked task found."}, status=404)
                
            serializer = TaskTrackedTimeSerializer(task)
            print("api hit of get track time", serializer.data)
            print(f"DEBUG: Serialized data: {serializer.data}")
            logger.info(f"Returning tracked time data for task {task.id}: {serializer.data}")
            
            return Response(serializer.data)
            
        except Task.DoesNotExist:
            print("DEBUG: Task.DoesNotExist exception raised")
            logger.error(f"Task not found for user {request.user.id}")
            return Response(ErrorMessages.STARTED_TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
            
        except MultipleObjectsReturned as e:
            print(f"DEBUG: MultipleObjectsReturned exception: {e}")
            logger.error(f"{ErrorMessages.SOMETHING_WENT_WRONG}: {e}")
            return Response(ErrorMessages.SOMETHING_WENT_WRONG, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"DEBUG: Unexpected error in GET request: {e}")
            logger.error(f"Unexpected error in tracked time GET request for user {request.user.id}: {e}")
            return Response(ErrorMessages.SOMETHING_WENT_WRONG, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StartTaskTracker(APIView):
    """
    Endpoint to start the tracker for a specific task.
    """
    permission_classes = [IsTaskOwner]
    tags = ['Tasks']

    def post(self, request, pk):
        """
        Start tracking time for a task identified by the pk parameter if tracking has not already started.
        """
        print(f"DEBUG: StartTaskTracker POST request - task_id: {pk}, user: {request.user.id}")
        logger.info(f"Start tracking request for task {pk} from user {request.user.id}")
        
        try:
            print(f"DEBUG: Attempting to retrieve task {pk} for user {request.user.id}")
            task = Task.objects.get(pk=pk, user=request.user)
            print(f"DEBUG: Task retrieved successfully - ID: {task.id}, Name: {getattr(task, 'name', 'N/A')}")
            logger.info(f"Task {pk} found for user {request.user.id}")
            
            self.check_object_permissions(self.request, task)
            print("DEBUG: Object permissions check passed")
            
        except Task.DoesNotExist:
            print(f"DEBUG: Task {pk} not found for user {request.user.id}")
            logger.error(f"Task {pk} not found for user {request.user.id}")
            return Response(ErrorMessages.TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            print(f"DEBUG: Error retrieving task {pk}: {e}")
            logger.error(f"Error retrieving task {pk} for user {request.user.id}: {e}")
            return Response(ErrorMessages.SOMETHING_WENT_WRONG, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Check if user already has an active tracking task
        print(f"DEBUG: Checking for existing active tracking tasks for user {request.user.id}")
        existing_active_task = Task.objects.filter(user=request.user, start_tracked_time__isnull=False).first()
        
        if existing_active_task:
            print(f"DEBUG: User {request.user.id} already has active tracking task: {existing_active_task.id}")
            logger.warning(f"User {request.user.id} attempted to start tracking task {pk} but already has active task {existing_active_task.id}")
            return Response(ErrorMessages.TASK_TRACKING_ALREADY_STARTED, status=status.HTTP_400_BAD_REQUEST)
        else:
            print(f"DEBUG: No existing active tracking tasks found for user {request.user.id}")

        # Check if this specific task is already being tracked
        print(f"DEBUG: Checking if task {pk} is already being tracked")
        print(f"DEBUG: Task {pk} current start_tracked_time: {task.start_tracked_time}")
        
        if task.start_tracked_time is None:
            current_time = timezone.now()
            task.start_tracked_time = current_time
            print(f"DEBUG: Setting start_tracked_time to: {current_time}")
            
            try:
                task.save()
                print(f"DEBUG: Task {pk} saved successfully with start_tracked_time")
                logger.info(f"Started tracking for task {pk} at {current_time}")
            except Exception as e:
                print(f"DEBUG: Error saving task {pk}: {e}")
                logger.error(f"Error saving task {pk} with start time: {e}")
                return Response(ErrorMessages.SOMETHING_WENT_WRONG, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print(f"DEBUG: Task {pk} already has start_tracked_time set: {task.start_tracked_time}")

        # Serialize task data
        try:
            serializer = TaskTrackedTimeSerializer(task)
            print(f"DEBUG: Task serialized successfully: {serializer.data}")
        except Exception as e:
            print(f"DEBUG: Error serializing task {pk}: {e}")
            logger.error(f"Error serializing task {pk}: {e}")

        # Emit socket.io event
        user_id = str(task.user.id)
        print(f"DEBUG: Emitting socket.io event 'task_started' to room: {user_id}")
        
        try:
            async_to_sync(sio.emit)(
                'task_started',
                serializer.data,
                room=user_id
            )
            print(f"DEBUG: Socket.io event emitted successfully for task {pk}")
            logger.info(f"Socket.io 'task_started' event emitted for task {pk}")
        except Exception as e:
            print(f"DEBUG: Error emitting socket.io event for task {pk}: {e}")
            logger.error(f"Error emitting socket.io event for task {pk}: {e}")

        # Schedule duration notification if enabled
        print(f"DEBUG: Task {pk} send_notification setting: {task.send_notification}")
        if task.send_notification:
            print(f"DEBUG: Scheduling duration notification for task {pk}")
            try:
                schedule_task_duration.send_with_options(args=(task.id,))
                print(f"DEBUG: Duration notification scheduled successfully for task {pk}")
                logger.info(f"Duration notification scheduled for task {pk}")
            except Exception as e:
                print(f"DEBUG: Error scheduling duration notification for task {pk}: {e}")
                logger.error(f"Error scheduling duration notification for task {pk}: {e}")
        else:
            print(f"DEBUG: Notifications disabled for task {pk}, skipping duration scheduling")

        print(f"DEBUG: StartTaskTracker completed successfully for task {pk}")
        logger.info(f"Task tracking started successfully for task {pk}")
        return Response(SuccessMessages.TASK_TRACKING_STARTED, status=status.HTTP_200_OK)


class StopTaskTracker(APIView):
    """
    Endpoint to stop the tracker for a specific task.
    """
    permission_classes = [IsTaskOwner]
    tags = ['Tasks']

    def post(self, request, pk):
        """
        Stop tracking time for a task identified by the pk parameter if tracking has been started.
        Ensures that the tracked time does not exceed the planned task duration.
        """
        print(f"DEBUG: StopTaskTracker POST request - task_id: {pk}, user: {request.user.id}")
        logger.info(f"Stop tracking request for task {pk} from user {request.user.id}")
        
        try:
            print(f"DEBUG: Attempting to retrieve task {pk}")
            task = Task.objects.get(pk=pk)
            print(f"DEBUG: Task {pk} retrieved - User: {task.user.id}, start_tracked_time: {task.start_tracked_time}")
            
            self.check_object_permissions(self.request, task)
            print("DEBUG: Object permissions check passed")
            logger.info(f"Task {pk} found and permissions verified")
            
        except Task.DoesNotExist:
            print(f"DEBUG: Task {pk} not found")
            logger.error(f"Task {pk} not found for stop tracking request")
            return Response(ErrorMessages.TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            print(f"DEBUG: Error retrieving task {pk}: {e}")
            logger.error(f"Error retrieving task {pk} for stop tracking: {e}")
            return Response(ErrorMessages.SOMETHING_WENT_WRONG, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        print(f"DEBUG: Checking if task {pk} has active tracking")
        print(f"DEBUG: Current start_tracked_time: {task.start_tracked_time}")
        print(f"DEBUG: Current tracked_time: {task.tracked_time}")
        
        if task.start_tracked_time is not None:
            current_time = timezone.now()
            session_duration = current_time - task.start_tracked_time
            print(f"DEBUG: Current time: {current_time}")
            print(f"DEBUG: Session duration: {session_duration}")
            
            # Calculate new total tracked time
            new_tracked_time = task.tracked_time + session_duration
            print(f"DEBUG: Previous tracked_time: {task.tracked_time}")
            print(f"DEBUG: New total tracked_time: {new_tracked_time}")
            
            # Update task
            task.tracked_time = new_tracked_time
            task.start_tracked_time = None
            
            try:
                task.save()
                print(f"DEBUG: Task {pk} updated successfully - tracking stopped")
                logger.info(f"Task {pk} tracking stopped. Session duration: {session_duration}, Total tracked: {new_tracked_time}")
            except Exception as e:
                print(f"DEBUG: Error saving task {pk} after stopping tracking: {e}")
                logger.error(f"Error saving task {pk} after stopping tracking: {e}")
                return Response(ErrorMessages.SOMETHING_WENT_WRONG, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Emit socket.io event
            print(f"DEBUG: Emitting socket.io 'task_stopped' event for task {pk}")
            try:
                async_to_sync(sio.emit)(
                    'task_stopped',
                    {
                        'task_id': task.id,
                        'message': 'Task tracking stopped',
                        'session_duration': str(session_duration),
                        'total_tracked_time': str(new_tracked_time)
                    },
                    room=str(task.user_id)
                )
                print(f"DEBUG: Socket.io 'task_stopped' event emitted successfully for task {pk}")
                logger.info(f"Socket.io 'task_stopped' event emitted for task {pk}")
            except Exception as e:
                print(f"DEBUG: Error emitting socket.io event for task {pk}: {e}")
                logger.error(f"Error emitting socket.io event for task {pk}: {e}")

            # Remove scheduled duration notification
            print(f"DEBUG: Removing scheduled duration notification for task {pk}")
            try:
                remove_scheduled_job.send_with_options(args=(task.pk, send_task_duration_reminder_notification.__name__))
                print(f"DEBUG: Scheduled job removal initiated for task {pk}")
                logger.info(f"Duration notification job removal initiated for task {pk}")
            except Exception as e:
                print(f"DEBUG: Error removing scheduled job for task {pk}: {e}")
                logger.error(f"Error removing scheduled job for task {pk}: {e}")

            print(f"DEBUG: StopTaskTracker completed successfully for task {pk}")
            logger.info(f"Task tracking stopped successfully for task {pk}")
            return Response(SuccessMessages.TASK_TRACKING_STOPPED, status=status.HTTP_200_OK)
            
        else:
            print(f"DEBUG: Task {pk} is not currently being tracked")
            logger.warning(f"Attempted to stop tracking for task {pk} but it's not currently being tracked")
            return Response(ErrorMessages.TASK_START_ERROR, status=status.HTTP_400_BAD_REQUEST)

print("DEBUG: Task tracking views module initialization complete")
from rest_framework.views import APIView
from rest_framework.response import Response
from api.tasks import scheduler

class ScheduledJobsDebugAPI(APIView):
    def get(self, request):
        jobs = scheduler.get_jobs()
        return Response([
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ])
