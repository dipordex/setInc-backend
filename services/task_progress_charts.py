from typing import Dict, Optional
from datetime import timedelta, datetime

from django.db.models import Sum

from api.models import Task
from api.tasks import get_timezone
from api.serializers import TaskSerializer
from services.top_activities import UserTaskRepository
from api.utils import get_start_of_week, beautify_duration


class TaskProgressChartsService(UserTaskRepository):
    """
    Service class to calculate and provide task progress charts and related data.
    """

    def __init__(self, user):
        """
        Initialize the service with a specific user.

        :param user: The user for whom to calculate task progress.
        """
        self.user = user
        self.user_timezone = user.timezone

    def get_today(self) -> datetime.date:
        """
        Returns the current date in the user's timezone.

        :return: The current date.
        """
        return datetime.now(get_timezone(self.user_timezone)).date()

    def calculate_progress_for_week(self, start_date: datetime.date) -> Dict[str, float]:
        """
        Calculates the task completion percentage for each day starting from a given date for one week.

        :param start_date: The start date from which to calculate task progress.
        :return: A dictionary mapping dates (YYYY-MM-DD format) to task completion percentages.
        """
        progress = {}
        for day in range(7):  # From start_date through the next 6 days
            date = start_date + timedelta(days=day)
            daily_tasks = self.get_tasks_for_user_for_today(self.get_tasks_for_user(self.user), date)
            total = daily_tasks.count()
            completed = daily_tasks.filter(done=True).count()
            progress[date.strftime("%Y-%m-%d")] = round((completed / total * 100), 2) if total else 0
        return progress

    def get_task_progress(self, today: datetime.date) -> Dict[str, Dict[str, float]]:
        """
        Aggregates the task completion percentages for the current and the last week.

        :param today: The current date to determine the weeks for comparison.
        :return: A dictionary with keys 'current_week' and 'last_week', each mapping dates to task completion percentages.
        """
        start_of_current_week = get_start_of_week(today, 0)  # Determine Monday of the current week
        start_of_last_week = start_of_current_week - timedelta(days=7)  # Determine Monday of the last week

        return {
            "current_week": self.calculate_progress_for_week(start_of_current_week),
            "last_week": self.calculate_progress_for_week(start_of_last_week),
        }

    def task_progress_today(self) -> Dict[str, Optional[float]]:
        """
        Calculates the progress of tasks for the current day, including completion percentage and tracked time.

        :return: A dictionary containing the task progress data for today.
        """
        tasks_for_today = self.get_tasks_for_user_for_today(self.get_tasks_for_user(self.user), self.get_today())
        total = tasks_for_today.count()
        completed = tasks_for_today.filter(done=True).count()
        tracked_time_sum = tasks_for_today.aggregate(Sum('tracked_time'))['tracked_time__sum'] or 0
        tracked_time_today = beautify_duration(tracked_time_sum)

        task_progress = {
            'completed_percentage': self.get_completed_percentage(total, completed),
            'tracked_time_today': tracked_time_today,
        }

        all_task_categories = self.get_all_task_categories()
        for category in all_task_categories:
            duration = tasks_for_today.filter(category=category).aggregate(Sum('tracked_time'))[
                           'tracked_time__sum'] or 0
            if duration and tracked_time_sum:
                task_progress[category.name] = round((duration * 100) / tracked_time_sum)
            else:
                task_progress[category.name] = 0
        return task_progress

    @staticmethod
    def get_completed_percentage(total: int, completed: int) -> int:
        """
        Calculates the completion percentage of tasks.

        :param total: The total number of tasks.
        :param completed: The number of completed tasks.
        :return: The completion percentage.
        """
        return round((completed * 100) / total) if total else 0

    def get_upcoming_task(self) -> Optional[Dict]:
        """
        Fetches the next upcoming task for the user.

        :return: Serialized data of the upcoming task or None if there's no upcoming task.
        """
        today = self.get_today()
        upcoming_task = Task.objects.filter(user=self.user, date__gte=today).order_by('date', 'start_time').first()
        return TaskSerializer(upcoming_task).data if upcoming_task else None
