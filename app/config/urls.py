from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from camera.views import CameraViewSet
from strawberry.django.views import GraphQLView
from config.schema import schema
from channels.views import stream_playback, stream_proxy

router = DefaultRouter()
router.register(r'cameras', CameraViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('graphql', csrf_exempt(GraphQLView.as_view(schema=schema))),
    path('api/streams/play/<str:token>/', stream_playback, name='stream-playback'),
    path('api/streams/proxy/<str:token>/', stream_proxy, name='stream-proxy'),
]