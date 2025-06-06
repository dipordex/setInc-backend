from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        import firebase_admin
        from django.conf import settings
        credentials = firebase_admin.credentials.Certificate(settings.FIREBASE_PATH)
        firebase_admin.initialize_app(credentials)
