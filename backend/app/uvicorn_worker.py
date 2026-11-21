"""Gunicorn worker configuration that never rewrites the direct peer address."""

from uvicorn.workers import UvicornWorker


class NoProxyHeadersUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {**UvicornWorker.CONFIG_KWARGS, "proxy_headers": False}
