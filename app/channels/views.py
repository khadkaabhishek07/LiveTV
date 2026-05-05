from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse
from jwt import ExpiredSignatureError, InvalidTokenError

from .models import Channel
from .services import decode_stream_token


def _get_channel_for_token(token: str):
    try:
        payload = decode_stream_token(token)
    except ExpiredSignatureError:
        return None, HttpResponseForbidden('Stream token expired.')
    except InvalidTokenError:
        return None, HttpResponseForbidden('Invalid stream token.')

    channel = get_object_or_404(Channel, id=payload.get('channel_id'), is_active=True)
    return channel, None


def _get_allowed_upstream_hosts():
    raw_hosts = getattr(settings, 'STREAM_UPSTREAM_ALLOWED_HOSTS', [])
    return {host.strip().lower() for host in raw_hosts if host and host.strip()}


def _is_allowed_upstream_url(url: str, channel: Channel):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    if not parsed.hostname:
        return False

    channel_host = urlparse(channel.stream_source_url).hostname or ''
    channel_host = channel_host.lower()
    upstream_host = parsed.hostname.lower()

    allowed_hosts = _get_allowed_upstream_hosts()
    if allowed_hosts and upstream_host not in allowed_hosts:
        return False
    return upstream_host == channel_host


def _fetch_upstream(url: str):
    req = Request(url, headers={'User-Agent': 'stream-weaver-proxy/1.0', 'Accept': '*/*'})
    with urlopen(req, timeout=15) as upstream:
        body = upstream.read()
        final_url = upstream.geturl()
        content_type = upstream.headers.get('Content-Type', 'application/octet-stream')
        return body, final_url, content_type


def _build_proxy_url(request, token: str, absolute_target_url: str):
    proxy_path = reverse('stream-proxy', kwargs={'token': token})
    return request.build_absolute_uri(f"{proxy_path}?{urlencode({'url': absolute_target_url}, quote_via=quote)}")


def _rewrite_playlist(playlist_text: str, request, token: str, base_url: str):
    rewritten = []
    for raw_line in playlist_text.splitlines():
        line = raw_line.strip()
        if not line:
            rewritten.append(raw_line)
            continue

        if line.startswith('#EXT-X-KEY:') and 'URI="' in raw_line:
            prefix, uri_tail = raw_line.split('URI="', 1)
            uri_value, suffix = uri_tail.split('"', 1)
            absolute_key_url = urljoin(base_url, uri_value)
            proxy_key_url = _build_proxy_url(request, token, absolute_key_url)
            rewritten.append(f'{prefix}URI="{proxy_key_url}"{suffix}')
            continue

        if line.startswith('#'):
            rewritten.append(raw_line)
            continue

        absolute_media_url = urljoin(base_url, line)
        rewritten.append(_build_proxy_url(request, token, absolute_media_url))
    return '\n'.join(rewritten) + '\n'


def stream_playback(request, token: str):
    channel, error = _get_channel_for_token(token)
    if error:
        return error

    if not _is_allowed_upstream_url(channel.stream_source_url, channel):
        return HttpResponseForbidden('Upstream stream host is not allowed.')

    try:
        body, final_url, _ = _fetch_upstream(channel.stream_source_url)
    except Exception:
        return HttpResponseForbidden('Unable to fetch upstream playlist.')

    playlist_text = body.decode('utf-8', errors='replace')
    rewritten_playlist = _rewrite_playlist(playlist_text, request, token, final_url)
    return HttpResponse(rewritten_playlist, content_type='application/vnd.apple.mpegurl')


def stream_proxy(request, token: str):
    channel, error = _get_channel_for_token(token)
    if error:
        return error

    target_url = request.GET.get('url')
    if not target_url:
        return HttpResponseBadRequest('Missing required query parameter: url')

    absolute_target = urljoin(channel.stream_source_url, target_url)
    if not _is_allowed_upstream_url(absolute_target, channel):
        return HttpResponseForbidden('Upstream proxy target is not allowed.')

    try:
        body, final_url, content_type = _fetch_upstream(absolute_target)
    except Exception:
        return HttpResponseForbidden('Unable to fetch upstream content.')

    if '.m3u8' in final_url.lower() or 'mpegurl' in content_type.lower():
        playlist_text = body.decode('utf-8', errors='replace')
        rewritten_playlist = _rewrite_playlist(playlist_text, request, token, final_url)
        return HttpResponse(rewritten_playlist, content_type='application/vnd.apple.mpegurl')

    return HttpResponse(body, content_type=content_type or 'application/octet-stream')
