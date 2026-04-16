from rest_framework.throttling import AnonRateThrottle


class SignupThrottle(AnonRateThrottle):
    rate = "5/hour"
    scope = "signup"


class LoginThrottle(AnonRateThrottle):
    rate = "10/hour"
    scope = "login"


class VerifyEmailThrottle(AnonRateThrottle):
    rate = "10/hour"
    scope = "verify_email"
