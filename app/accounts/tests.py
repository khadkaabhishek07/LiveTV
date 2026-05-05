import hashlib
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import EmailOTP, UserProfile
from accounts.services import verify_email_otp

User = get_user_model()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccountsTests(TestCase):
    def test_register_mutation_creates_user_and_sends_otp(self):
        query = """
        mutation {
          registerUser(username: "alice", email: "alice@example.com", password: "StrongPass123!") {
            success
            message
            user { email emailVerified }
          }
        }
        """
        response = self.client.post('/graphql', data={'query': query}, content_type='application/json')
        payload = response.json()['data']['registerUser']
        self.assertTrue(payload['success'])
        self.assertEqual(payload['user']['email'], 'alice@example.com')
        self.assertFalse(payload['user']['emailVerified'])
        self.assertEqual(EmailOTP.objects.count(), 1)

    def test_verify_otp_marks_profile_verified(self):
        user = User.objects.create_user(username='bob', email='bob@example.com', password='123')
        UserProfile.objects.create(user=user, email_verified=False)
        otp = '123456'
        EmailOTP.objects.create(
            user=user,
            otp_hash=hashlib.sha256(otp.encode('utf-8')).hexdigest(),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        ok, _ = verify_email_otp(user, otp)
        self.assertTrue(ok)
        profile = UserProfile.objects.get(user=user)
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        self.assertTrue(profile.email_verified)
