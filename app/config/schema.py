from typing import Optional

import strawberry
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from jwt import ExpiredSignatureError, InvalidTokenError
from strawberry.types import Info

from accounts.models import UserProfile
from accounts.services import create_and_send_email_otp, decode_token, issue_auth_tokens, verify_email_otp
from channels.models import Channel
from channels.services import build_playback_url, issue_stream_token

User = get_user_model()


@strawberry.type
class ApiError:
    code: str
    message: str


@strawberry.type
class UserNode:
    id: int
    username: str
    email: str
    email_verified: bool


@strawberry.type
class AuthPayload:
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[UserNode] = None
    errors: list[ApiError] = strawberry.field(default_factory=list)


@strawberry.type
class BasicPayload:
    success: bool
    message: str
    errors: list[ApiError] = strawberry.field(default_factory=list)


@strawberry.type
class ChannelNode:
    id: int
    name: str
    slug: str
    channel_number: int
    logo_url: str
    is_active: bool
    stream_source_url: str


@strawberry.type
class ChannelPayload:
    success: bool
    message: str
    channel: Optional[ChannelNode] = None
    errors: list[ApiError] = strawberry.field(default_factory=list)


@strawberry.type
class PlaybackPayload:
    success: bool
    message: str
    playback_url: Optional[str] = None
    expires_in_seconds: Optional[int] = None
    errors: list[ApiError] = strawberry.field(default_factory=list)


def _to_user_node(user: User) -> UserNode:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return UserNode(
        id=user.id,
        username=user.username,
        email=user.email,
        email_verified=profile.email_verified,
    )


def _to_channel_node(channel: Channel) -> ChannelNode:
    return ChannelNode(
        id=channel.id,
        name=channel.name,
        slug=channel.slug,
        channel_number=channel.channel_number,
        logo_url=channel.logo_url,
        is_active=channel.is_active,
        stream_source_url=channel.stream_source_url,
    )


def _get_access_user(info: Info):
    request = info.context['request']
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.lower().startswith('bearer '):
        return None, ApiError(code='UNAUTHENTICATED', message='Missing Bearer token.')
    token = auth_header.split(' ', 1)[1].strip()
    try:
        payload = decode_token(token, expected_type='access')
        user = User.objects.filter(id=payload.get('user_id')).first()
        if not user:
            return None, ApiError(code='UNAUTHENTICATED', message='User not found.')
        return user, None
    except ExpiredSignatureError:
        return None, ApiError(code='TOKEN_EXPIRED', message='Access token expired.')
    except InvalidTokenError:
        return None, ApiError(code='UNAUTHENTICATED', message='Invalid access token.')


def _get_verified_user(info: Info):
    user, error = _get_access_user(info)
    if error:
        return None, error
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if not profile.email_verified:
        return None, ApiError(code='EMAIL_NOT_VERIFIED', message='Verify your email first.')
    return user, None


@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info) -> Optional[UserNode]:
        user, error = _get_access_user(info)
        if error:
            return None
        return _to_user_node(user)

    @strawberry.field
    def channels(self, info: Info) -> list[ChannelNode]:
        user, error = _get_verified_user(info)
        if error or not user:
            return []
        return [_to_channel_node(channel) for channel in Channel.objects.filter(is_active=True)]

    @strawberry.field
    def channel_by_slug(self, info: Info, slug: str) -> Optional[ChannelNode]:
        user, error = _get_verified_user(info)
        if error or not user:
            return None
        channel = Channel.objects.filter(slug=slug, is_active=True).first()
        return _to_channel_node(channel) if channel else None

    @strawberry.field
    def get_playback_url(self, info: Info, channel_id: int) -> PlaybackPayload:
        user, error = _get_verified_user(info)
        if error:
            return PlaybackPayload(success=False, message='Not authorized.', errors=[error])
        channel = Channel.objects.filter(id=channel_id, is_active=True).first()
        if not channel:
            return PlaybackPayload(
                success=False,
                message='Channel not found.',
                errors=[ApiError(code='NOT_FOUND', message='Channel does not exist.')],
            )
        token = issue_stream_token(user_id=user.id, channel_id=channel.id)
        playback_url = build_playback_url(info.context['request'], token)
        return PlaybackPayload(
            success=True,
            message='Playback URL generated.',
            playback_url=playback_url,
            expires_in_seconds=settings.STREAM_TOKEN_TTL_SECONDS,
        )


@strawberry.type
class Mutation:
    @strawberry.mutation
    def register_user(self, username: str, email: str, password: str) -> AuthPayload:
        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            return AuthPayload(
                success=False,
                message='Registration failed.',
                errors=[ApiError(code='USER_EXISTS', message='Username or email already exists.')],
            )
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
        except IntegrityError:
            return AuthPayload(
                success=False,
                message='Registration failed.',
                errors=[ApiError(code='USER_EXISTS', message='Username or email already exists.')],
            )
        UserProfile.objects.get_or_create(user=user)
        create_and_send_email_otp(user)
        access_token, refresh_token = issue_auth_tokens(user)
        return AuthPayload(
            success=True,
            message='Registration successful. OTP sent to email.',
            access_token=access_token,
            refresh_token=refresh_token,
            user=_to_user_node(user),
        )

    @strawberry.mutation
    def send_email_otp(self, email: str) -> BasicPayload:
        user = User.objects.filter(email=email).first()
        if not user:
            return BasicPayload(
                success=False,
                message='User not found.',
                errors=[ApiError(code='NOT_FOUND', message='No user registered with this email.')],
            )
        create_and_send_email_otp(user)
        return BasicPayload(success=True, message='OTP sent to email.')

    @strawberry.mutation
    def verify_email_otp(self, email: str, otp: str) -> BasicPayload:
        user = User.objects.filter(email=email).first()
        if not user:
            return BasicPayload(
                success=False,
                message='User not found.',
                errors=[ApiError(code='NOT_FOUND', message='No user registered with this email.')],
            )
        ok, msg = verify_email_otp(user, otp)
        if not ok:
            return BasicPayload(
                success=False,
                message='Email verification failed.',
                errors=[ApiError(code='INVALID_OTP', message=msg)],
            )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        return BasicPayload(success=True, message=msg)

    @strawberry.mutation
    def login(self, username_or_email: str, password: str) -> AuthPayload:
        user = User.objects.filter(email=username_or_email).first()
        username = user.username if user else username_or_email
        user = authenticate(username=username, password=password)
        if not user:
            return AuthPayload(
                success=False,
                message='Invalid credentials.',
                errors=[ApiError(code='INVALID_CREDENTIALS', message='Username/email or password is incorrect.')],
            )
        access_token, refresh_token = issue_auth_tokens(user)
        return AuthPayload(
            success=True,
            message='Login successful.',
            access_token=access_token,
            refresh_token=refresh_token,
            user=_to_user_node(user),
        )

    @strawberry.mutation
    def refresh_access_token(self, refresh_token: str) -> AuthPayload:
        try:
            payload = decode_token(refresh_token, expected_type='refresh')
        except ExpiredSignatureError:
            return AuthPayload(
                success=False,
                message='Refresh failed.',
                errors=[ApiError(code='TOKEN_EXPIRED', message='Refresh token expired.')],
            )
        except InvalidTokenError:
            return AuthPayload(
                success=False,
                message='Refresh failed.',
                errors=[ApiError(code='INVALID_TOKEN', message='Invalid refresh token.')],
            )
        user = User.objects.filter(id=payload.get('user_id')).first()
        if not user:
            return AuthPayload(
                success=False,
                message='Refresh failed.',
                errors=[ApiError(code='UNAUTHENTICATED', message='User not found.')],
            )
        access_token, next_refresh = issue_auth_tokens(user)
        return AuthPayload(
            success=True,
            message='Token refreshed.',
            access_token=access_token,
            refresh_token=next_refresh,
            user=_to_user_node(user),
        )

    @strawberry.mutation
    def create_channel(
        self,
        info: Info,
        name: str,
        channel_number: int,
        logo_url: str,
        stream_source_url: str,
        is_active: bool = True,
    ) -> ChannelPayload:
        user, error = _get_verified_user(info)
        if error or not user:
            return ChannelPayload(success=False, message='Not authorized.', errors=[error])
        channel = Channel.objects.create(
            name=name,
            channel_number=channel_number,
            logo_url=logo_url,
            stream_source_url=stream_source_url,
            is_active=is_active,
        )
        return ChannelPayload(success=True, message='Channel created.', channel=_to_channel_node(channel))

    @strawberry.mutation
    def update_channel(
        self,
        info: Info,
        channel_id: int,
        name: Optional[str] = None,
        channel_number: Optional[int] = None,
        logo_url: Optional[str] = None,
        stream_source_url: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> ChannelPayload:
        user, error = _get_verified_user(info)
        if error or not user:
            return ChannelPayload(success=False, message='Not authorized.', errors=[error])
        channel = Channel.objects.filter(id=channel_id).first()
        if not channel:
            return ChannelPayload(
                success=False,
                message='Channel not found.',
                errors=[ApiError(code='NOT_FOUND', message='Channel does not exist.')],
            )
        if name is not None:
            channel.name = name
        if channel_number is not None:
            channel.channel_number = channel_number
        if logo_url is not None:
            channel.logo_url = logo_url
        if stream_source_url is not None:
            channel.stream_source_url = stream_source_url
        if is_active is not None:
            channel.is_active = is_active
        channel.save()
        return ChannelPayload(success=True, message='Channel updated.', channel=_to_channel_node(channel))

    @strawberry.mutation
    def delete_channel(self, info: Info, channel_id: int) -> BasicPayload:
        user, error = _get_verified_user(info)
        if error or not user:
            return BasicPayload(success=False, message='Not authorized.', errors=[error])
        channel = Channel.objects.filter(id=channel_id).first()
        if not channel:
            return BasicPayload(
                success=False,
                message='Channel not found.',
                errors=[ApiError(code='NOT_FOUND', message='Channel does not exist.')],
            )
        channel.delete()
        return BasicPayload(success=True, message='Channel deleted.')


schema = strawberry.Schema(query=Query, mutation=Mutation)
