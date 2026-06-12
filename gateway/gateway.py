import requests
import uuid
from sentence_transformers import SentenceTransformer


class CognitiveGateway:
    def __init__(self, rust_daemon_url="http://127.0.0.1:3000"):
        print("Initializing SentenceTransformer (all-MiniLM-L6-v2)...")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.daemon_url = rust_daemon_url
        print(f"CognitiveGateway connected to {self.daemon_url}")

    def commit_memory(self, text: str, salience: float):
        """
        Generates a 384D embedding for the text and POSTs it to the Rust daemon.
        """
        print(f"--> Encoding: '{text}' (salience={salience})")
        embedding = self.model.encode(text).tolist()

        payload = {
            "id": str(uuid.uuid4()),
            "text": text,
            "embedding": embedding,
            "salience": salience,
        }

        try:
            response = requests.post(f"{self.daemon_url}/inject", json=payload)
            response.raise_for_status()
            print(f"    [Success] Injected. Daemon response: {response.json()}")
        except Exception as e:
            print(f"    [Error] Failed to inject: {e}")

    def recall_state(self):
        """
        Pings the Rust daemon to get the currently dominating attractor.
        """
        try:
            print("--> Recalling dominant state from HRSA...")
            response = requests.get(f"{self.daemon_url}/recall")
            response.raise_for_status()
            data = response.json()
            print(f"    [Result] Dominant Attractor: {data.get('recovered_text')}")
            return data.get("recovered_text")
        except Exception as e:
            print(f"    [Error] Failed to recall: {e}")
            return None
