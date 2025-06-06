import logging
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, TransactionTestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from setinc.settings import REST_FRAMEWORK as api_settings

AUTH_HEADER_TYPES = api_settings.get('AUTH_HEADER_TYPES')


class APITestUser(APITestCase):

    @staticmethod
    def create_user(username):
        user = get_user_model().objects.create_user(username=username)
        user.is_active = True
        user.set_password('somepass')
        user.save()
        return user

    def authorize(self, user, **additional_headers):
        token, created = Token.objects.get_or_create(user=user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'{AUTH_HEADER_TYPES} {token}', **additional_headers)

    def create_and_authorize_user(self, username, **additional_headers):
        user = self.create_user(username)
        self.authorize(user, **additional_headers)
        return user

    def logout(self, **additional_headers):
        self.client.credentials(**additional_headers)

    @staticmethod
    def url_with_querystring(path, **kwargs):
        """Set request params to url"""
        return path + '?' + urlencode(kwargs)


class BaseTestCase(APITestUser, TransactionTestCase):
    LOGGER = logging.getLogger(__name__)
    # fixtures = ['webapi/fixtures/initial_state']
    anonymous_user = AnonymousUser

    def setUp(self):
        self.user = self.anonymous_user
        self.user = self.create_user('some@domain.com')
        self.LOGGER.info(f'TEST: Login with {self.user} credentials')


class ReceiverConnectionTestCase(TestCase):
    """TestCase that allows asserting that a given receiver is connected to a signal.

    Important: this will work correctly providing you:
        1. Do not import or patch anything in the module containing the receiver in any django.test.TestCase.
        2. Do not import (except in the context of a method) the module containing the receiver in any test module.

    This is because as soon as you import/patch, the receiver will be connected by your test and will be connected
    for the entire test suite run.

    If you want to test the behaviour of the receiver, you may do this providing it is a unittest.TestCase, and there
    is no import from the receiver module in that test module.

    Usage:

        # myapp/receivers.py
        from django.dispatch import receiver
        from apples.signals import apple_eaten
        from apples.models import Apple

        @receiver(apple_eaten, sender=Apple)
        def my_receiver(sender, **kwargs):
            pass


        # tests/integration_tests.py
        from apples.signals import apple_eaten
        from apples.models import Apple

        class TestMyReceiverConnection(ReceiverConnectionTestCase):
            def test_connection(self):
                self.assert_receiver_is_connected('myapp.receivers.my_receiver', signal=apple_eaten, sender=Apple)

    """

    @staticmethod
    def assert_receiver_is_connected(receiver_string, signal, sender):
        receivers = signal._live_receivers(sender)
        receiver_strings = ["{}.{}".format(r.__module__, r.__name__) for r in receivers]
        if receiver_string not in receiver_strings:
            raise AssertionError('{} is not connected to signal.'.format(receiver_string))
