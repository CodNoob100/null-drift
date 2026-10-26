"""Issue #176: HTTP 4xx/5xx escaped the LangGraph snapshot/restore helpers'
error handling because they caught only httpx.RequestError, while
raise_for_status() raises httpx.HTTPStatusError (an HTTPError, not a
RequestError). These tests pin the handling through httpx.MockTransport —
no gateway, no network."""

from __future__ import annotations

import logging

import httpx
import pytest

from nulldrift_agents import NullDriftLangGraphStore


def _store(handler) -> NullDriftLangGraphStore:
    store = NullDriftLangGraphStore(gateway_url="http://gw.test")
    store.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://gw.test")
    return store


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "status"),
    [
        ("take_snapshot", "/snapshot", 500),
        ("take_snapshot", "/snapshot", 404),
        ("restore_from_snapshot", "/restore", 503),
        ("restore_from_snapshot", "/restore", 401),
    ],
)
async def test_http_errors_are_logged_not_raised(method, path, status, caplog):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(status)

    store = _store(handler)
    with caplog.at_level(logging.ERROR, logger="root"):
        await getattr(store, method)(("thread", "one"))

    assert calls == [path]
    assert any("failed" in m and str(status) in m for m in caplog.messages), caplog.messages


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["take_snapshot", "restore_from_snapshot"])
async def test_transport_failures_still_logged(method, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    store = _store(handler)
    with caplog.at_level(logging.ERROR, logger="root"):
        await getattr(store, method)(("thread", "one"))

    assert any("failed" in m for m in caplog.messages)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["take_snapshot", "restore_from_snapshot"])
async def test_success_is_silent(method, caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    store = _store(handler)
    with caplog.at_level(logging.ERROR, logger="root"):
        await getattr(store, method)(("thread", "one"))

    assert not [m for m in caplog.messages if "failed" in m]
