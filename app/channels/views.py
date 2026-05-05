from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from jwt import ExpiredSignatureError, InvalidTokenError

from .models import Channel
from .services import decode_stream_token


def stream_playback(request, token: str):
    try:
        payload = decode_stream_token(token)
    except ExpiredSignatureError:
        return HttpResponseForbidden('Stream token expired.')
    except InvalidTokenError:
        return HttpResponseForbidden('Invalid stream token.')

    channel = get_object_or_404(Channel, id=payload.get('channel_id'), is_active=True)
    return redirect(channel.stream_source_url)
