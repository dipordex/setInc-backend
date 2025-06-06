from datetime import timedelta

from api.utils import get_start_of_week
from api.models import Task, TaskCategory


class UserTaskRepository:
    @staticmethod
    def get_tasks_for_user(user):
        return Task.objects.filter(user=user)

    @staticmethod
    def get_tasks_count_for_user(user_tasks):
        return user_tasks.count()

    @staticmethod
    def get_tasks_for_user_for_today(user_tasks, today):
        return user_tasks.filter(date=today)

    @staticmethod
    def get_completed_tasks_count_by_user_tasks(user_tasks) -> int:
        return user_tasks.filter(done=True).count()

    @staticmethod
    def get_completed_tasks(user_tasks):
        return user_tasks.filter(done=True)

    @staticmethod
    def get_completed_tasks_count(completed_tasks):
        return completed_tasks.count()

    @staticmethod
    def get_all_task_categories():
        return TaskCategory.objects.all()


class TopActivitiesService(UserTaskRepository):

    def get_top_activities(self, today, user_tasks):
        top_activities = {}
        start_of_current_week = get_start_of_week(today, 0)
        for day in range(7):
            date = start_of_current_week + timedelta(days=day)
            user_tasks_for_day = self.get_tasks_for_user_for_today(user_tasks, date)
            completed_tasks = self.get_completed_tasks(user_tasks_for_day)
            top_activities[date.strftime("%Y-%m-%d")] = self.calculate_activities(
                self.get_tasks_count_for_user(user_tasks_for_day), self.get_completed_tasks_count(completed_tasks),
                completed_tasks, self.get_all_task_categories())
        return top_activities

    @staticmethod
    def calculate_activities(tasks_count, completed_tasks_count, completed_tasks, categories):
        activities = {'all': 0}
        if tasks_count:
            activities['all'] = round((completed_tasks_count * 100) / tasks_count)
        for category in categories:
            category_completed_tasks = completed_tasks.filter(category=category).count()
            activities[category.name] = round((category_completed_tasks * 100) / completed_tasks_count) \
                if completed_tasks_count else 0
        return activities
