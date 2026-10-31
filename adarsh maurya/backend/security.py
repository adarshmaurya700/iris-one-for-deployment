"""Shared request policies and URL guards for billable verification routes."""
import ipaddress
import math
import socket
import threading
import time
from collections import OrderedDict
from secrets import compare_digest
from urllib.parse import urlparse
from fastapi import HTTPException, Request
from runtime_config import credential, production


class SlidingWindowRateLimiter:
    def __init__(self, max_requests, window_seconds, scope='Request rate limit'):
        self.max_requests, self.window_seconds, self.scope = max_requests, window_seconds, scope
        self.hits = OrderedDict()
        self.lock = threading.Lock()

    def check(self, request: Request):
        # Uvicorn alone may resolve forwarded addresses from explicitly trusted proxies.
        key = request.client.host if request.client else 'unknown'
        now = time.monotonic()
        with self.lock:
            while self.hits and ((next(iter(self.hits.values()))[-1] if next(iter(self.hits.values())) else 0) <= now - self.window_seconds):
                self.hits.popitem(last=False)
            hits = [t for t in self.hits.pop(key, []) if t > now - self.window_seconds]
            if len(hits) >= self.max_requests:
                self.hits[key] = hits
                retry = max(1, math.ceil(self.window_seconds - (now - (hits[0] if hits else now))))
                raise HTTPException(429, self.scope + ' exceeded. Please try again later.', headers={'Retry-After': str(retry)})
            if len(self.hits) >= 10000:
                self.hits.popitem(last=False)
            self.hits[key] = hits + [now]


assistant_limit = SlidingWindowRateLimiter(30, 600, 'Assistant request limit')
verification_limit = SlidingWindowRateLimiter(10, 600, 'Verification request limit')
auth_limit = SlidingWindowRateLimiter(12, 600, 'Sign-in request limit')
sync_limit = SlidingWindowRateLimiter(3, 600, 'Catalog refresh limit')


def require_admin(request: Request):
    expected = credential('IRIS_ADMIN_KEY')
    supplied = request.headers.get('X-IRIS-Admin-Key', '')
    if expected and compare_digest(supplied, expected):
        return
    # Local development diagnostics are available only to direct local callers.
    local = request.client and request.client.host in ('127.0.0.1', '::1', 'testclient')
    if not production() and not expected and local and not request.headers.get('origin'):
        return
    raise HTTPException(403, 'Administrator credentials are required.')


def require_verification_access(request: Request):
    verification_limit.check(request)
    if production():
        from auth import get_current_user
        from database import get_db
        db = get_db()
        try:
            get_current_user(request, db)
        finally:
            db.close()


def public_url(value, resolve=True):
    parsed = urlparse(str(value or ''))
    host = (parsed.hostname or '').rstrip('.').lower()
    try:
        port = parsed.port
    except ValueError:
        raise ValueError('Invalid source URL port.') from None
    if parsed.scheme not in ('http', 'https') or not host or parsed.username or parsed.password or port not in (None, 80, 443):
        raise ValueError('A public HTTP(S) source URL is required.')
    if host == 'localhost' or '.' not in host or host.endswith(('.local', '.internal', '.localhost')):
        raise ValueError('Local source addresses are not allowed.')
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        addresses = []
        if resolve:
            addresses = [ipaddress.ip_address(entry[4][0]) for entry in socket.getaddrinfo(host, port or 443, type=socket.SOCK_STREAM)]
    if any(not address.is_global for address in addresses):
        raise ValueError('Private source addresses are not allowed.')
    return parsed.geturl()
