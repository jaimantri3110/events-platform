import logging

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import EmailOTP

logger = logging.getLogger(__name__)

User = get_user_model()


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit OTP."""
    import secrets

    return str(secrets.randbelow(900000) + 100000)


def create_and_send_otp(user) -> None:
    """Generate OTP, store hashed, and send via email."""
    raw_otp = generate_otp()
    otp_record = EmailOTP(
        user=user,
        expires_at=timezone.now() + timezone.timedelta(minutes=EmailOTP.TTL_MINUTES),
    )
    otp_record.set_otp(raw_otp)
    otp_record.save()

    send_mail(
        subject="Your verification code",
        message=f"Your OTP is: {raw_otp}. It expires in {EmailOTP.TTL_MINUTES} minutes.",
        from_email=None,
        recipient_list=[user.email],
    )
    logger.info("otp_sent", extra={"user_id": user.id, "email": user.email})


def verify_otp(email: str, submitted_otp: str) -> tuple:
    """
    Verify OTP with atomic locking to prevent race conditions.
    Returns (success: bool, error_code: str | None)
    """
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return False, "user_not_found"

    with transaction.atomic():
        otp_record = (
            EmailOTP.objects.select_for_update()
            .filter(user=user, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if otp_record is None:
            return False, "no_active_otp"

        if otp_record.attempts >= EmailOTP.MAX_ATTEMPTS:
            return False, "max_attempts_exceeded"

        otp_record.attempts += 1
        otp_record.save(update_fields=["attempts"])

        if timezone.now() > otp_record.expires_at:
            return False, "otp_expired"

        if not otp_record.verify_otp(submitted_otp):
            logger.warning(
                "otp_verification_failed",
                extra={"user_id": user.id, "attempts": otp_record.attempts},
            )
            return False, "invalid_otp"

        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])

        user.profile.is_email_verified = True
        user.profile.save(update_fields=["is_email_verified"])

        logger.info("email_verified", extra={"user_id": user.id})
        return True, None
