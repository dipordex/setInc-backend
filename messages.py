class ErrorMessages:
    # PHONE NUMBER

    VERIFICATION_CODE_ERROR = "Verification code must contain only digits."
    WRONG_PHONE_NUMBER_FORMAT = "Phone number is not valid."

    # TASK
    TASK_START_ERROR = {"error": "Task tracking has not started or already stopped."}
    TASK_TIME_ZONE_ERROR = "An error occurred in TaskProgressChartsAPI: {}"
    TASK_START_TIME_ERROR = "Task start time is not set."
    TASK_NOT_FOUND = {"error": "Task not found."}
    STARTED_TASK_NOT_FOUND = {"error": "Started task not found."}
    TASK_TRACKING_ALREADY_STARTED = {"error": "You currently have an ongoing task."}
    TASK_CREATE_ERROR = {'message': 'You can not create a new task.',  'type': 'subscription'}
    TASK_TIME_IS_ALREADY_PASSED = 'Task time is already passed or too close for a {}-minute reminder.'
    END_TIME_BEFORE_START_TIME = "End time before start time"
    TASK_NOT_YOURS = {'message': 'This task does not belong to you.'}
    MAX_ACTIVE_ALARMS = 'You have reached the maximum number of active alarms without a subscription.'
    # ALARM
    ALARM_NOT_YOURS = {'message': 'You cannot edit alarms that are not yours.'}

    # OTHER
    SOMETHING_WENT_WRONG = {"error": "Something went wrong."}
    INCORRECT_DATE_FORMAT = {"error": "Incorrect date format, should be YY/MM/DD"}
    WRONG_TIMEZONE = "Could not find a timezone for {}."
    DATE_IN_PAST = "Date in past"


class SuccessMessages:

    # TASK
    TASK_TRACKING_STOPPED = {"status": "Task tracking stopped"}
    TASK_TRACKING_STARTED = {"status": "Task tracking started"}
