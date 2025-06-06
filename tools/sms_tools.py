import logging
from typing import List

from django.conf import settings

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class TwilioService:
    def __init__(self) -> None:
        self.messaging_service_sid = settings.TWILIO_PHONE_NUMBER,
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        self.test_numbers = [
            "+61482089896",  # for tests
            '+37455555555',
            '+380911111111',
            '+79888888888',
            '+37493444444',
            '+37493941213',
            "+6777624123",  # Solomon Island
        ]

    def _send_sms(self, text: str, phone_number: str) -> True:
        """SMS sending if number is not in test numbers"""

        if phone_number in self.test_numbers:
            return False

        try:
            self.client.messages.create(
                body=text,
                from_=self.messaging_service_sid,
                to=phone_number,
            )
            return True
        except TwilioRestException as e:
            logger.error(f"Twilio | Error: {e}")
            return False

    def get_test_numbers(self) -> List[str]:
        return self.test_numbers

    def send_verification_code(self, phone_number: str, verification_code: str) -> bool:
        """Sending verification code by SMS"""

        text = f"Your verification code is: {verification_code}"
        return self._send_sms(text=text, phone_number=phone_number)


twilio = TwilioService()
