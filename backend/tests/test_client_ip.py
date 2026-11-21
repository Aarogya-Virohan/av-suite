from starlette.requests import Request

from app.core.config import settings
from app.core.dependencies import get_client_ip


def make_request(peer: str | None, headers: dict[str, str] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
            "client": (peer, 12345) if peer is not None else None,
            "server": ("testserver", 80),
        }
    )


def test_get_client_ip_uses_direct_peer_without_forwarded_headers(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "")
    assert get_client_ip(make_request("192.0.2.10")) == "192.0.2.10"


def test_get_client_ip_ignores_spoofed_xff_from_untrusted_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8")
    request = make_request("192.0.2.10", {"X-Forwarded-For": "203.0.113.5"})
    assert get_client_ip(request) == "192.0.2.10"


def test_get_client_ip_ignores_spoofed_cloudflare_header_from_untrusted_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8")
    request = make_request("192.0.2.10", {"CF-Connecting-IP": "203.0.113.5"})
    assert get_client_ip(request) == "192.0.2.10"


def test_get_client_ip_accepts_valid_forwarded_ip_from_trusted_proxy(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8")
    request = make_request("10.0.0.4", {"CF-Connecting-IP": "203.0.113.5"})
    assert get_client_ip(request) == "203.0.113.5"


def test_get_client_ip_falls_back_on_malformed_forwarded_values(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8")
    malformed_xff = make_request(
        "10.0.0.4", {"X-Forwarded-For": "203.0.113.5, not-an-ip"}
    )
    malformed_cf = make_request("10.0.0.4", {"CF-Connecting-IP": "203.0.113.5:123"})
    assert get_client_ip(malformed_xff) == "10.0.0.4"
    assert get_client_ip(malformed_cf) == "10.0.0.4"


def test_get_client_ip_walks_xff_chain_right_to_left(monkeypatch):
    monkeypatch.setattr(
        settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8,198.51.100.0/24"
    )
    request = make_request(
        "10.0.0.4",
        {"X-Forwarded-For": "203.0.113.9, 198.51.100.8, 10.0.0.3"},
    )
    assert get_client_ip(request) == "203.0.113.9"


def test_get_client_ip_handles_empty_or_missing_direct_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", "10.0.0.0/8")
    assert get_client_ip(make_request(None, {"CF-Connecting-IP": "203.0.113.5"})) == "unknown"
    assert get_client_ip(make_request("", {"X-Forwarded-For": "203.0.113.5"})) == "unknown"
