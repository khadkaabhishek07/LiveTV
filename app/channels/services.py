from datetime import timedelta

import jwt
from django.conf import settings
from django.urls import reverse
from django.utils import timezone


def issue_stream_token(*, user_id: int, channel_id: int) -> str:
    now = timezone.now()
    payload = {
        'type': 'stream',
        'user_id': user_id,
        'channel_id': channel_id,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(seconds=settings.STREAM_TOKEN_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, settings.GRAPHQL_JWT_SECRET, algorithm='HS256')


def decode_stream_token(token: str):
    payload = jwt.decode(token, settings.GRAPHQL_JWT_SECRET, algorithms=['HS256'])
    if payload.get('type') != 'stream':
        raise jwt.InvalidTokenError('Invalid token type.')
    return payload


def build_playback_url(request, token: str) -> str:
    path = reverse('stream-playback', kwargs={'token': token})
    return request.build_absolute_uri(path)
