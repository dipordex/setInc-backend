from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet

app_name = 'api'

__all__ = ['urlpatterns']

urlpatterns = [
    path('get-verification-code/', GetVerificationCodeAPI.as_view()),
    path('verify-verification-code/', VerifyVerificationCodeAPI.as_view()),
    path('user/', UserAPI.as_view()),
    path('default-alarm/', DefaultAlarmAPI.as_view()),
    path('create-task/', CreateTaskAPI.as_view()),
    path('task/<int:pk>', TaskAPI.as_view()),
    path('tasks-list/<str:date>', TasksListByDateAPI.as_view()),
    path('tasks-list/', TasksListAPI.as_view()),
    path('task-categories/', TaskCategoriesAPI.as_view()),
    path('charts/tasks-progress/', TaskProgressChartsAPI.as_view()),
    path('charts/top-activities/', TopActivitiesChartsAPI.as_view()),
    path('get-timezones/', TimezoneListView.as_view()),
    path('stopwatch/', StopwatchAPI.as_view()),
    path('stopwatch/<int:pk>', StopwatchAPI.as_view(),name='stopwatch-detail'),
    path('stopwatch/<int:pk>/', StopwatchActionAPI.as_view(), name='stopwatch-action'),
    # path('stopwatch/<int:pk>/stop/', StopStopwatchAPI.as_view(), name='stop-stopwatch'),
    path('edit-stopwatch/<int:pk>', StopwatchEditAPI.as_view()),
    path('lap/', LapAPI.as_view()),
    path('stopwatch-laps/<int:pk>', StopwatchLapsAPI.as_view()),

    path('devices/', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}),
         name='create_fcm_device'),
    path('activate-existing-devices/', ActivateExistingDevices.as_view()),
    path('deactivate-existing-devices/', DeactivateExistingDevices.as_view()),
    path('check-fcm-token/', CheckFCMTokenAPIView.as_view()),

    path('token/refresh/', TokenRefreshView.as_view(),
         name='token_refresh'),
    path('notes/', NotesAPI.as_view(), name='notes-detail'), # patch api for notes
]

router = DefaultRouter(trailing_slash=False)
router.register('validate_receipt', ReceiptViewSet, basename='validate_receipt')
urlpatterns += router.urls
