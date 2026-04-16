from .base import *  # noqa: F401, F403

DEBUG = False

# Railway (and most PaaS) terminate TLS at the edge proxy and forward
# plain HTTP internally.  SECURE_SSL_REDIRECT=True would cause an
# infinite redirect loop because Django sees HTTP on the internal hop.
# Instead, trust the X-Forwarded-Proto header set by the Railway proxy.
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
