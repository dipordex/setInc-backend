from django.urls import path
from .views import TaskTrackedTimeDetailView, StartTaskTracker, StopTaskTracker

urlpatterns = [
    path('', TaskTrackedTimeDetailView.as_view(), name='task_tracked_time'),
    path('<int:pk>/start/', StartTaskTracker.as_view(), name='start_task_tracker'),
    path('<int:pk>/stop/', StopTaskTracker.as_view(), name='stop_task_tracker'),
]
