import os
import pytest
import asyncio
import httpx
import time
from nulldrift_agents import NullDriftCrewStorage, NullDriftLangGraphStore

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:8000")

# Wait for gateway to fully boot (Sentence Transformers takes ~10s to load)


@pytest.fixture(scope="session")
def gateway_ready():
    """Wait for the gateway to become available."""

    for _ in range(30):
        try:
            httpx.get(f"{GATEWAY_URL}/")
            return
        except httpx.ConnectError:
            time.sleep(1)

    pytest.fail("Gateway failed to boot in time")


@pytest.mark.asyncio
async def test_crew_ai_storage(gateway_ready):
    storage = NullDriftCrewStorage(
        gateway_url=GATEWAY_URL,
        thread_id="test_crew_1",
    )

    # Save payload
    payload = {
        "role": "researcher",
        "content": "The null-drift daemon uses HRSA.",
    }
    storage.save(payload)

    # Wait for processing
    await asyncio.sleep(1)

    # Search
    results = storage.search("null-drift")
    assert len(results) > 0
    assert "HRSA" in results[0]["content"]


@pytest.mark.asyncio
async def test_langgraph_store(gateway_ready):
    store = NullDriftLangGraphStore(
        gateway_url=GATEWAY_URL,
    )
    namespace = ("test", "langgraph", "agent1")

    # Async put
    await store.aput(
        namespace,
        "memory_key",
        {"state": "Active", "context": "Testing LangGraph integration"},
    )

    # Wait for processing
    await asyncio.sleep(1)

    # Async get
    result = await store.aget(namespace, "memory_key")
    assert result is not None
    assert result["state"] == "Active"

    # Snapshot
    await store.take_snapshot(namespace)

    # Restore
    await store.restore_from_snapshot(namespace)

    # Verify it still exists after restore
    result2 = await store.aget(namespace, "memory_key")
    assert result2 is not None
    assert result2["state"] == "Active"
