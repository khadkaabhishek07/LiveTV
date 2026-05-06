from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter

from camera.views import CameraViewSet
from strawberry.django.views import GraphQLView
from config.schema import schema

# 👇 UPDATED IMPORTS (IMPORTANT)
from channels.views import stream_playback, stream_proxy


router = DefaultRouter()
router.register(r'cameras', CameraViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),

    # GraphQL
    path('graphql', csrf_exempt(GraphQLView.as_view(schema=schema))),

    # =========================
    # 🔥 STREAM ROUTES (NEW)
    # =========================

    # Main stream (HLS playlist entry)
    path(
        'api/streams/play/<int:channel_id>/',
        stream_playback,
        name='stream-playback'
    ),

    # Proxy for segments (.ts / keys / nested m3u8)
    path(
        'api/streams/proxy/<int:channel_id>/',
        stream_proxy,
        name='stream-proxy'
    ),
]