from pathlib import Path

from app.uvicorn_worker import NoProxyHeadersUvicornWorker


ROOT = Path(__file__).resolve().parents[2]


def test_deployment_launch_commands_disable_uvicorn_proxy_headers():
    dockerfile = (ROOT / "backend/Dockerfile").read_text()
    compose = (ROOT / "backend/docker-compose.yml").read_text()
    render = (ROOT / "render.yaml").read_text()
    main = (ROOT / "backend/app/main.py").read_text()

    assert "--no-proxy-headers" in dockerfile
    assert "--no-proxy-headers" in compose
    assert "--no-proxy-headers" in render
    assert "proxy_headers=False" in main
    assert NoProxyHeadersUvicornWorker.CONFIG_KWARGS["proxy_headers"] is False
