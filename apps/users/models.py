from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Role(models.TextChoices):
    SEEKER = "seeker", "Seeker"
    FACILITATOR = "facilitator", "Facilitator"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user.email} ({self.role})"


class EmailOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="otps",
    )
    # Stores PBKDF2 hash, not the raw OTP — 128 chars for PBKDF2
    otp = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    MAX_ATTEMPTS = 5
    TTL_MINUTES = 5

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_used"]),
            models.Index(fields=["expires_at"]),
        ]

    def set_otp(self, raw_otp: str) -> None:
        """Hash and store the OTP."""
        self.otp = make_password(raw_otp)

    def verify_otp(self, raw_otp: str) -> bool:
        """Check submitted OTP against stored hash."""
        return check_password(raw_otp, self.otp)

    def __str__(self):
        return f"OTP for {self.user.email} (used={self.is_used})"
