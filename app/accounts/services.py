import hashlib
import hmac
import random
from datetime import timedelta

import jwt
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailOTP


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode('utf-8')).hexdigest()


def create_and_send_email_otp(user):
    otp = f"{random.randint(0, 999999):06d}"
    expires_at = timezone.now() + timedelta(minutes=settings.OTP_TTL_MINUTES)
    otp_row = EmailOTP.objects.create(
        user=user,
        otp_hash=_hash_otp(otp),
        expires_at=expires_at,
    )
    send_mail(
        subject='Your verification OTP',
        message=f'Your OTP is {otp}. It expires in {settings.OTP_TTL_MINUTES} minutes.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    return otp_row


def verify_email_otp(user, otp: str):
    otp_row = EmailOTP.objects.filter(user=user, consumed_at__isnull=True).order_by('-created_at').first()
    if not otp_row:
        return False, 'No active OTP found. Please request a new OTP.'
    if otp_row.is_expired:
        return False, 'OTP has expired. Please request a new OTP.'
    if otp_row.attempts >= settings.OTP_MAX_ATTEMPTS:
        return False, 'OTP attempts exceeded. Please request a new OTP.'

    otp_row.attempts += 1
    otp_row.save(update_fields=['attempts'])

    if not hmac.compare_digest(otp_row.otp_hash, _hash_otp(otp)):
        return False, 'Invalid OTP.'

    otp_row.consumed_at = timezone.now()
    otp_row.save(update_fields=['consumed_at'])
    return True, 'Email verified successfully.'


def issue_auth_tokens(user):
    now = timezone.now()
    access_payload = {
        'user_id': user.id,
        'type': 'access',
        'exp': int((now + timedelta(minutes=settings.GRAPHQL_ACCESS_TOKEN_TTL_MINUTES)).timestamp()),
        'iat': int(now.timestamp()),
    }
    refresh_payload = {
        'user_id': user.id,
        'type': 'refresh',
        'exp': int((now + timedelta(days=settings.GRAPHQL_REFRESH_TOKEN_TTL_DAYS)).timestamp()),
        'iat': int(now.timestamp()),
    }
    return (
        jwt.encode(access_payload, settings.GRAPHQL_JWT_SECRET, algorithm='HS256'),
        jwt.encode(refresh_payload, settings.GRAPHQL_JWT_SECRET, algorithm='HS256'),
    )


def decode_token(token: str, expected_type: str):
    payload = jwt.decode(token, settings.GRAPHQL_JWT_SECRET, algorithms=['HS256'])
    if payload.get('type') != expected_type:
        raise jwt.InvalidTokenError('Invalid token type.')
    return payload
