"""
设置页数据源选择已接后端：GET/POST /api/v1/settings/datasource 即时生效。

验证：
- 默认 source=fallback，各外部 provider 可用性正确（配置含免 key URL 时 enabled 且 mode=keyless）。
- POST 选外部源 -> source 更新、USE_EXTERNAL_DATA 翻 True；POST fallback -> 翻回 False。
- 全程不触碰网络（monkeypatch 掉行情流，避免 reseed 触发真实请求）。
"""
import os
import sys

# 保证单独运行本文件时也能 import app（与整套 pytest 运行时的 sys.path 一致）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

import app.config as cfg

# 用临时库隔离，避免与共享 financesim.db 争锁
_tmp = __import__("tempfile").mktemp(suffix=".db")
cfg.settings.DATABASE_URL = f"sqlite+aiosqlite:///{_tmp}"

from app.main import app  # noqa: E402
from app.core import runtime_settings as rs  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    # 阻断 reseed 真实网络请求：让 market_stream.get_market_stream() 返回 None
    import app.services.market_stream as ms

    monkeypatch.setattr(ms, "get_market_stream", lambda *a, **k: None)
    with TestClient(app) as c:
        yield c
    # 复位为默认，避免影响其它用例
    rs.set_data_source("fallback")


def test_default_source_is_fallback(client):
    r = client.get("/api/v1/settings/datasource")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "fallback"
    # 配置默认带免 key URL -> provider 默认 enabled 且 mode=keyless
    for name in ("alpha_vantage", "fred", "news_api"):
        assert body["available"][name]["enabled"] is True
        assert body["available"][name]["mode"] == "keyless"


def test_post_external_enables_use_external_data(client, monkeypatch):
    r = client.post(
        "/api/v1/settings/datasource",
        json={"source": "alpha-vantage"},
    )
    assert r.status_code == 200
    assert r.json()["source"] == "alpha-vantage"
    assert cfg.settings.USE_EXTERNAL_DATA is True
    # 再切回 fallback 应复位
    r2 = client.post(
        "/api/v1/settings/datasource",
        json={"source": "fallback"},
    )
    assert r2.json()["source"] == "fallback"
    assert cfg.settings.USE_EXTERNAL_DATA is False


def test_post_invalid_source_falls_back(client):
    r = client.post("/api/v1/settings/datasource", json={"source": "bogus"})
    assert r.status_code == 200
    assert r.json()["source"] == "fallback"
    assert cfg.settings.USE_EXTERNAL_DATA is False
