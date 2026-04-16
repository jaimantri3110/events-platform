import logging

from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import Profile
from .serializers import LoginSerializer, SignupSerializer, VerifyEmailSerializer
from .services import create_and_send_otp, verify_otp
from .throttles import LoginThrottle, SignupThrottle, VerifyEmailThrottle

logger = logging.getLogger(__name__)

User = get_user_model()


class SignupView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [SignupThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Register a new user",
        request=SignupSerializer,
        responses={
            201: OpenApiExample(
                "Success",
                value={"detail": "Account created. Please verify your email with the OTP sent.", "email": "user@example.com"},
            ),
            400: OpenApiExample(
                "Error",
                value={"detail": "Email already registered.", "code": "email_exists"},
            ),
        },
    )
    def post(self, request):
        if "username" in request.data:
            return Response(
                {"detail": "Username field is not allowed.", "code": "username_not_allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        role = serializer.validated_data["role"]

        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "Email already registered.", "code": "email_exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                user = User.objects.create_user(username=email, email=email, password=password)
                Profile.objects.create(user=user, role=role)
                create_and_send_otp(user)
        except IntegrityError:
            return Response(
                {"detail": "Email already registered.", "code": "email_exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("user_signup", extra={"email": email, "role": role})
        return Response(
            {"detail": "Account created. Please verify your email with the OTP sent.", "email": email},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [VerifyEmailThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Verify email with OTP",
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiExample("Success", value={"detail": "Email verified successfully."}),
            400: OpenApiExample("Error", value={"detail": "Invalid OTP.", "code": "invalid_otp"}),
            429: OpenApiExample("Too many attempts", value={"detail": "Max attempts exceeded.", "code": "max_attempts_exceeded"}),
        },
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        submitted_otp = serializer.validated_data["otp"]

        success, error_code = verify_otp(email, submitted_otp)

        if not success:
            if error_code == "max_attempts_exceeded":
                return Response(
                    {"detail": "Max OTP attempts exceeded.", "code": "max_attempts_exceeded"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            return Response(
                {"detail": "Invalid or expired OTP.", "code": error_code},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @extend_schema(
        tags=["Auth"],
        summary="Login and get JWT tokens",
        request=LoginSerializer,
        responses={
            200: OpenApiExample(
                "Success",
                value={
                    "access": "eyJ...",
                    "refresh": "eyJ...",
                    "user": {"id": 1, "email": "user@example.com", "role": "seeker"},
                },
            ),
            401: OpenApiExample("Invalid credentials", value={"detail": "Invalid credentials.", "code": "invalid_credentials"}),
            403: OpenApiExample("Not verified", value={"detail": "Email not verified.", "code": "email_not_verified"}),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            logger.warning("user_login_failed", extra={"email": email, "reason": "user_not_found"})
            return Response(
                {"detail": "Invalid credentials.", "code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            logger.warning("user_login_failed", extra={"email": email, "reason": "invalid_credentials"})
            return Response(
                {"detail": "Invalid credentials.", "code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not hasattr(user, "profile") or not user.profile.is_email_verified:
            return Response(
                {"detail": "Email not verified.", "code": "email_not_verified"},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        logger.info("user_login_success", extra={"user_id": user.id})

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {"id": user.id, "email": user.email, "role": user.profile.role},
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(TokenRefreshView):
    """Standard JWT token refresh."""
