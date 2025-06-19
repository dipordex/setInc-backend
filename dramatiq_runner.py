# dramatiq_runner.py
import os
import django
import dramatiq

# STEP 1: Load Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setinc.settings")  # Replace with your project.settings
django.setup()

# STEP 2: Import your actor module
import api.tasks  # Ensure this imports your actors

# STEP 3: Run Dramatiq worker programmatically
if __name__ == "__main__":
    from dramatiq.cli import main
    main()
