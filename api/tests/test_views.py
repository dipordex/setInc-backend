from django.test import TestCase

from api.serializers import PhoneNumberSerializer


class PhoneNumberSerializerTestCase(TestCase):
    def test_valid_phone_number(self):
        # Test the serializer with a valid phone number
        serializer = PhoneNumberSerializer(data={'phone_number': '+67756789'})
        self.assertTrue(serializer.is_valid())

    def test_invalid_phone_number_length(self):
        # Test the serializer with an invalid phone number length
        serializer = PhoneNumberSerializer(data={'phone_number': '12345'})
        self.assertFalse(serializer.is_valid())
