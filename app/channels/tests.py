from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from accounts.services import issue_auth_tokens
from channels.models import Channel

User = get_user_model()


class ChannelsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='verified', email='v@example.com', password='StrongPass123!')
        UserProfile.objects.create(user=self.user, email_verified=True)
        self.channel = Channel.objects.create(
            name='Test Channel',
            slug='test-channel',
            channel_number=1,
            logo_url='https://example.com/logo.png',
            stream_source_url='http://example.com/live/playlist.m3u8',
            is_active=True,
        )
        access, _ = issue_auth_tokens(self.user)
        self.auth_header = {'HTTP_AUTHORIZATION': f'Bearer {access}'}

    def test_verified_user_can_get_playback_url(self):
        query = f"""
        query {{
          getPlaybackUrl(channelId: {self.channel.id}) {{
            success
            playbackUrl
            errors {{ code }}
          }}
        }}
        """
        response = self.client.post('/graphql', data={'query': query}, content_type='application/json', **self.auth_header)
        payload = response.json()['data']['getPlaybackUrl']
        self.assertTrue(payload['success'])
        self.assertIn('/api/streams/play/', payload['playbackUrl'])

    def test_unverified_user_cannot_access_channels(self):
        unverified = User.objects.create_user(username='nov', email='nov@example.com', password='StrongPass123!')
        UserProfile.objects.create(user=unverified, email_verified=False)
        access, _ = issue_auth_tokens(unverified)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {access}'}
        query = """
        query {
          channels {
            id
            name
          }
        }
        """
        response = self.client.post('/graphql', data={'query': query}, content_type='application/json', **headers)
        payload = response.json()['data']['channels']
        self.assertEqual(payload, [])
