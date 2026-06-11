import httpx
import json
import logging
from typing import Any, Dict, List, Optional

# Protocol Stubs (Assuming CrewAI and LangGraph are installed in the user's environment)
class StorageBackend:
    pass

class BaseStore:
    pass

class NullDriftCrewStorage(StorageBackend):
    def __init__(self, gateway_url: str = "http://127.0.0.1:8000", thread_id: str = "default_crew"):
        self.gateway_url = gateway_url.rstrip("/")
        self.thread_id = thread_id
        
    def save(self, payload: Dict[str, Any]) -> None:
        """Injects the payload into the continuous state."""
        text_payload = json.dumps(payload)
        data = {
            "text": text_payload,
            "salience": 1.0  # Force high salience to ensure it locks into the AMN index
        }
        try:
            with httpx.Client() as client:
                res = client.post(f"{self.gateway_url}/inject", params={"thread_id": self.thread_id}, json=data, timeout=5.0)
                res.raise_for_status()
        except Exception as e:
            logging.error(f"Failed to save to null-drift: {e}")

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Recalls the dominant state."""
        try:
            with httpx.Client() as client:
                res = client.get(f"{self.gateway_url}/recall", params={"thread_id": self.thread_id}, timeout=5.0)
                res.raise_for_status()
                data = res.json()
                if data.get("recovered_text"):
                    return [json.loads(data["recovered_text"])]
        except Exception as e:
            logging.error(f"Failed to search null-drift: {e}")
        return []
        
    def take_snapshot(self) -> None:
        """Forces the daemon to flush this specific thread's state to disk."""
        try:
            with httpx.Client() as client:
                client.post(f"{self.gateway_url}/snapshot", params={"thread_id": self.thread_id}, timeout=5.0)
        except Exception as e:
            logging.error(f"Failed to take snapshot: {e}")

    def restore_from_snapshot(self) -> None:
        """Loads this specific thread's state from disk, overwriting the Moka cache."""
        try:
            with httpx.Client() as client:
                client.post(f"{self.gateway_url}/restore", params={"thread_id": self.thread_id}, timeout=5.0)
        except Exception as e:
            logging.error(f"Failed to restore snapshot: {e}")


class NullDriftLangGraphStore(BaseStore):
    def __init__(self, gateway_url: str = "http://127.0.0.1:8000"):
        self.gateway_url = gateway_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=5.0)
        
    async def aput(self, namespace: tuple[str, ...], key: str, value: dict[str, Any]) -> None:
        """
        Maps LangGraph's namespace to a specific null-drift thread_id, giving every
        namespace its own isolated 10,000D phase space.
        """
        thread_id = "_".join(namespace)
        text_payload = json.dumps({"key": key, "value": value})
        data = {
            "text": text_payload,
            "salience": 1.0
        }
        try:
            res = await self.client.post(f"{self.gateway_url}/inject", params={"thread_id": thread_id}, json=data)
            res.raise_for_status()
        except httpx.RequestError as e:
            logging.error(f"NullDrift LangGraph async put failed: {e}")

    async def aget(self, namespace: tuple[str, ...], key: str) -> Optional[dict]:
        thread_id = "_".join(namespace)
        try:
            res = await self.client.get(f"{self.gateway_url}/recall", params={"thread_id": thread_id})
            res.raise_for_status()
            data = res.json()
            if data.get("recovered_text"):
                parsed = json.loads(data["recovered_text"])
                if parsed.get("key") == key:
                    return parsed.get("value")
        except httpx.RequestError as e:
            logging.error(f"NullDrift LangGraph async get failed: {e}")
        return None

    async def take_snapshot(self, namespace: tuple[str, ...]) -> None:
        thread_id = "_".join(namespace)
        try:
            res = await self.client.post(f"{self.gateway_url}/snapshot", params={"thread_id": thread_id})
            res.raise_for_status()
        except httpx.RequestError as e:
            logging.error(f"NullDrift LangGraph async snapshot failed: {e}")

    async def restore_from_snapshot(self, namespace: tuple[str, ...]) -> None:
        thread_id = "_".join(namespace)
        try:
            res = await self.client.post(f"{self.gateway_url}/restore", params={"thread_id": thread_id})
            res.raise_for_status()
        except httpx.RequestError as e:
            logging.error(f"NullDrift LangGraph async restore failed: {e}")
