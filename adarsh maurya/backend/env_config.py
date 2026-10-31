"""Compatibility accessor using the single environment loader."""
import os
import env_loader  # noqa: F401


def get_env(name, default=''):
    return (os.environ.get(name) or default).strip()
