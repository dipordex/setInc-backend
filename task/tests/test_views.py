from api.models import User
from api.models import Task

from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from rest_framework.test import APITestCase
from api.utils import get_token_for_user


class TaskTrackerTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(phone_number='+6121121212', password='test_password')
        tokens = get_token_for_user(self.user)
        self.task = Task.objects.create(
            title="Test Task",
            description="Test Description",
            date=timezone.now().date(),
            user=self.user
        )
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens['access_token'])

    def test_start_task_tracker(self):
        """
        Ensure we can start the task tracker.
        """
        url = reverse('task:start_task_tracker', kwargs={'pk': self.task.pk})
        response = self.client.post(url)
        self.task.refresh_from_db()  # Refresh the task object after modification
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.task.start_tracked_time)

    def test_stop_task_tracker(self):
        """
        Ensure we can stop the task tracker.
        """
        # First, start the tracker
        self.task.start_tracked_time = timezone.now()
        self.task.save()

        url = reverse('task:stop_task_tracker', kwargs={'pk': self.task.pk})
        response = self.client.post(url)
        self.task.refresh_from_db()  # Refresh the task object after modification
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(self.task.start_tracked_time)
        self.assertIsNotNone(self.task.tracked_time)

    def test_get_tracked_time_detail(self):
        """
        Ensure we can retrieve tracked time details for a task.
        """
        url = reverse('task:task_tracked_time')
        response = self.client.get(url)
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND))

    def test_prevent_start_tracking_if_already_started(self):
        """
        Ensure we cannot start tracking if it's already started.
        """
        self.task.start_tracked_time = timezone.now()
        self.task.save()

        url = reverse('task:start_task_tracker', kwargs={'pk': self.task.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_prevent_stopping_tracking_if_not_started(self):
        """
        Ensure we cannot stop tracking if it hasn't been started.
        """
        url = reverse('task:stop_task_tracker', kwargs={'pk': self.task.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
