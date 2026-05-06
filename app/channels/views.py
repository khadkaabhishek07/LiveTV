from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse

from .models import Channel


# 🔥 Fetch upstream stream
def _fetch_upstream(url: str):
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': '*/*',
        'Referer': url,
        'Origin': 'https://google.com',
    })

    with urlopen(req, timeout=15) as upstream:
        body = upstream.read()
        final_url = upstream.geturl()
        content_type = upstream.headers.get('Content-Type', 'application/octet-stream')
        return body, final_url, content_type


# 🔥 Build proxy URL for segments
def _build_proxy_url(request, channel_id: int, absolute_target_url: str):
    proxy_path = reverse('stream-proxy', kwargs={'channel_id': channel_id})
    return request.build_absolute_uri(
        f"{proxy_path}?{urlencode({'url': absolute_target_url}, quote_via=quote)}"
    )


# 🔥 Rewrite playlist (VERY IMPORTANT)
def _rewrite_playlist(playlist_text: str, request, channel_id: int, base_url: str):
    rewritten = []

    for raw_line in playlist_text.splitlines():
        line = raw_line.strip()

        if not line:
            rewritten.append(raw_line)
            continue

        # handle encryption keys
        if line.startswith('#EXT-X-KEY:') and 'URI="' in raw_line:
            prefix, uri_tail = raw_line.split('URI="', 1)
            uri_value, suffix = uri_tail.split('"', 1)

            absolute_key_url = urljoin(base_url, uri_value)
            proxy_key_url = _build_proxy_url(request, channel_id, absolute_key_url)

            rewritten.append(f'{prefix}URI="{proxy_key_url}"{suffix}')
            continue

        if line.startswith('#'):
            rewritten.append(raw_line)
            continue

        # media segment
        absolute_media_url = urljoin(base_url, line)
        rewritten.append(_build_proxy_url(request, channel_id, absolute_media_url))

    return '\n'.join(rewritten) + '\n'


# 🔥 MAIN PLAYBACK (NO TOKEN)
def stream_playback(request, channel_id: int):
    channel = get_object_or_404(Channel, id=channel_id, is_active=True)

    try:
        body, final_url, content_type = _fetch_upstream(channel.stream_source_url)
    except Exception as e:
        return HttpResponseForbidden(f'Upstream fetch failed: {str(e)}')

    # if it's playlist → rewrite
    if '.m3u8' in final_url.lower() or 'mpegurl' in content_type.lower():
        playlist_text = body.decode('utf-8', errors='replace')
        rewritten_playlist = _rewrite_playlist(playlist_text, request, channel_id, final_url)

        return HttpResponse(
            rewritten_playlist,
            content_type='application/vnd.apple.mpegurl'
        )

    # fallback
    return HttpResponse(body, content_type=content_type)


# 🔥 PROXY SEGMENTS
def stream_proxy(request, channel_id: int):
    channel = get_object_or_404(Channel, id=channel_id, is_active=True)

    target_url = request.GET.get('url')
    if not target_url:
        return HttpResponseBadRequest('Missing url')

    absolute_target = urljoin(channel.stream_source_url, target_url)

    try:
        body, final_url, content_type = _fetch_upstream(absolute_target)
    except Exception as e:
        return HttpResponseForbidden(f'Proxy fetch failed: {str(e)}')

    # handle nested playlists
    if '.m3u8' in final_url.lower() or 'mpegurl' in content_type.lower():
        playlist_text = body.decode('utf-8', errors='replace')
        rewritten_playlist = _rewrite_playlist(playlist_text, request, channel_id, final_url)

        return HttpResponse(
            rewritten_playlist,
            content_type='application/vnd.apple.mpegurl'
        )

    return HttpResponse(body, content_type=content_type)