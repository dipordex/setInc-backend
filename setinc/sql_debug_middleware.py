import time
import traceback
from django.db import connection, reset_queries
from django.conf import settings

class QueryDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            reset_queries()
            start_time = time.time()

        response = self.get_response(request)

        if settings.DEBUG:
            total_time = time.time() - start_time
            num_queries = len(connection.queries)
            print(f"\n🛠️  SQL Debug Info - {num_queries} queries in {total_time:.2f}s:")

            for i, query in enumerate(connection.queries):
                # Attempt to extract file and line number from stack
                file_info = self._find_query_origin()

                print(f"\n{i + 1}. {query['sql']} ({query['time']}s)")
                if file_info:
                    print(f"   ↪ Origin: {file_info}")

            print("—" * 100)

        return response

    def _find_query_origin(self):
        stack = traceback.extract_stack()
        for frame in reversed(stack):
            if "site-packages" not in frame.filename and "sql_debug_middleware.py" not in frame.filename:
                return f"{frame.filename}:{frame.lineno}"
        return None
