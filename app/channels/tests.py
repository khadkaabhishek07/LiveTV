from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch

from accounts.models import UserProfile
from accounts.services import issue_auth_tokens
from channels.models import Channel
from channels.services import issue_stream_token

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
            stream_source_url='http://110.44.127.109:8081/live/playlist.m3u8',
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

    @patch('channels.views.urlopen')
    def test_stream_playback_rewrites_playlist_urls(self, mock_urlopen):
        class MockResponse:
            def __init__(self, body, final_url, content_type='application/vnd.apple.mpegurl'):
                self._body = body
                self._final_url = final_url
                self.headers = {'Content-Type': content_type}

            def read(self):
                return self._body

            def geturl(self):
                return self._final_url

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_urlopen.return_value = MockResponse(
            body=b"#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"enc.key\"\nsegment1.ts\n",
            final_url='http://110.44.127.109:8081/path/master.m3u8',
        )

        stream_token = issue_stream_token(user_id=self.user.id, channel_id=self.channel.id)
        response = self.client.get(f'/api/streams/play/{stream_token}/')
        self.assertEqual(response.status_code, 200)
        text = response.content.decode('utf-8')
        self.assertIn('/api/streams/proxy/', text)
        self.assertIn('url=http%3A%2F%2F110.44.127.109%3A8081%2Fpath%2Fsegment1.ts', text)

    @patch('channels.views.urlopen')
    def test_stream_proxy_blocks_invalid_host(self, mock_urlopen):
        mock_urlopen.side_effect = AssertionError('urlopen should not be called')
        token = issue_stream_token(user_id=self.user.id, channel_id=self.channel.id)
        response = self.client.get(
            f'/api/streams/proxy/{token}/',
            {'url': 'http://example.com/segment1.ts'},
        )
        self.assertEqual(response.status_code, 403)
