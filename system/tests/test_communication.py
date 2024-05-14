from django.test import TestCase
from django.conf import settings
from django.core.mail import send_mail
from users.models import User


class CommunicationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(None, 'somepassword', "test@test2.no", "98753321")

    def test_email_sending(self):
        return_value = self.user.send_email('Test Email', 'Test Body')
        self.assertEqual(return_value, 1)

    def test_sms_sending(self):
        return_value = self.user.send_sms("this is test sms msg")
        self.assertIsNotNone(return_value)
        print("sms sid: {}".format(return_value))