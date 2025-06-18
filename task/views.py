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


class TaskTrackedTimeDetailView(APIView):
    """
    Retrieve the tracked time details for a specific task.
    """
    tags = ['Tasks']

    # def get_object(self):
    #     """
    #     Helper method to get the task object, and check if the user has the permission to view it.
    #     """
    #     # return Task.objects.get(user=self.request.user, start_tracked_time__isnull=False)
    # 
    def get_object(self):
        return Task.objects.filter(user=self.request.user, start_tracked_time__isnull=False).first()        
    @swagger_auto_schema(tags=['Tasks'], operation_description="Method to get tracked time")
    def get(self, request):
        """
        Retrieve and return the tracked time for the specified task.
        """
        try:
            task = self.get_object()
            if not task:
                return Response({"error": "No active tracked task found."}, status=404)
            serializer = TaskTrackedTimeSerializer(self.get_object())
            print("api hit of get track time", serializer.data)
            return Response(serializer.data)
        except Task.DoesNotExist:
            return Response(ErrorMessages.STARTED_TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        except MultipleObjectsReturned as e:
            logger.error(f"{ErrorMessages.SOMETHING_WENT_WRONG}: {e}")
            return Response(ErrorMessages.SOMETHING_WENT_WRONG, status=status.HTTP_400_BAD_REQUEST)


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
        try:
            task = Task.objects.get(pk=pk, user=request.user)
            self.check_object_permissions(self.request, task)
        except Task.DoesNotExist:
            return Response(ErrorMessages.TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)

        if Task.objects.filter(user=request.user, start_tracked_time__isnull=False).exists():
            return Response(ErrorMessages.TASK_TRACKING_ALREADY_STARTED, status=status.HTTP_400_BAD_REQUEST)

        if task.start_tracked_time is None:
            task.start_tracked_time = timezone.now()
            task.save()

        serializer = TaskTrackedTimeSerializer(task)
        user_id = str(task.user.id)

        # Emit socket.io event to all of user's connected devices
        async_to_sync(sio.emit)(
            'task_started',
            serializer.data,
            room=user_id
            
        )

        if task.send_notification:
            schedule_task_duration.send_with_options(args=(task.id,))

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
        try:
            task = Task.objects.get(pk=pk)
            self.check_object_permissions(self.request, task)
        except Task.DoesNotExist:
            return Response(ErrorMessages.TASK_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)

        if task.start_tracked_time is not None:
            task.tracked_time += timezone.now() - task.start_tracked_time
            task.start_tracked_time = None
            task.save()
          # Emit socket.io event to all of user's connected devices
            async_to_sync(sio.emit)(
                'task_stopped',
                {
                    'task_id': task.id,
                    'message': 'Task tracking stopped',
                    # 'duration': str(tracked_duration)
                },
                room=str(task.user_id)
            )
            remove_scheduled_job.send_with_options(args=(task.pk,  send_task_duration_reminder_notification.__name__))
            return Response(SuccessMessages.TASK_TRACKING_STOPPED, status=status.HTTP_200_OK)
        return Response(ErrorMessages.TASK_START_ERROR, status=status.HTTP_400_BAD_REQUEST)
