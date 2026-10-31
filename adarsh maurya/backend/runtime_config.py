"""Shared non-secret runtime policy. Environment files never override host settings."""
import os
import secrets
from pathlib import Path
import env_loader  # noqa: F401


def production():
    return os.environ.get('IRIS_ENV', 'development').lower() == 'production'


def mode():
    value = os.environ.get('IRIS_MODE', 'live').lower()
    if value not in ('live', 'demo'):
        raise RuntimeError('IRIS_MODE must be live or demo.')
    return value


def credential(name):
    value = os.environ.get(name, '').strip()
    return value if value and not value.upper().startswith(('YOUR_', 'REPLACE_', 'CHANGE_ME')) else ''


def signing_secret():
    value = credential('JWT_SECRET')
    if value:
        if len(value.encode()) < 32 or value == 'iris_one_secret_key_2026':
            raise RuntimeError('JWT_SECRET must contain at least 32 bytes and must not use the old demo secret.')
        return value
    if production():
        raise RuntimeError('JWT_SECRET is required in production (at least 32 random bytes).')
    directory = Path(os.environ.get('IRIS_DATA_DIR') or (Path(os.environ['LOCALAPPDATA']) / 'IRIS-one' if os.environ.get('LOCALAPPDATA') else Path.home() / '.local/share/iris-one'))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / '.jwt-secret'
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        value = path.read_text(encoding='utf-8').strip()
    else:
        value = secrets.token_urlsafe(48)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(value)
    if len(value) < 32:
        raise RuntimeError('The local signing secret is invalid; configure JWT_SECRET explicitly.')
    return value


def validate_runtime():
    mode()
    if production():
        signing_secret()
        if not credential('IRIS_ADMIN_KEY') or len(credential('IRIS_ADMIN_KEY')) < 32:
            raise RuntimeError('IRIS_ADMIN_KEY (at least 32 bytes) is required in production.')
        if '*' in os.environ.get('ALLOWED_ORIGINS', ''):
            raise RuntimeError('Production ALLOWED_ORIGINS must list explicit origins, or be empty for same-origin hosting.')
