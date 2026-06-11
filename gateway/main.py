from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import requests
import os
from sentence_transformers import SentenceTransformer

app = FastAPI(title="null-drift-gateway", description="ML Inference Gateway for the HRSA daemon")

# Use SentenceTransformer cache
print("Loading model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
NULLD_URL = os.getenv("NULLD_URL", "http://127.0.0.1:3000")

class TextRequest(BaseModel):
    text: str = Field(..., max_length=2000, description="The textual event to encode")
    salience: float = Field(..., ge=0.0, le=1.0, description="Salience weight for the memory (0.0 to 1.0)")

class RecallResponse(BaseModel):
    recovered_text: str | None

@app.post("/inject")
async def inject_memory(payload: TextRequest, thread_id: str = Query("default")):
    """
    Encodes the semantic string into a 384D embedding and forwards it to the Rust daemon.
    """
    embedding = model.encode(payload.text).tolist()
    
    daemon_payload = {
        "text": payload.text,
        "embedding": embedding,
        "salience": payload.salience
    }
    
    try:
        response = requests.post(f"{NULLD_URL}/inject", params={"thread_id": thread_id}, json=daemon_payload, timeout=2.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Daemon error: {str(e)}")

@app.get("/recall", response_model=RecallResponse)
async def recall_state(steps_ago: int = None, thread_id: str = Query("default")):
    """
    Queries the Rust daemon for the dominating attractor.
    """
    params = {"thread_id": thread_id}
    if steps_ago is not None:
        params["steps_ago"] = steps_ago
        
    try:
        response = requests.get(f"{NULLD_URL}/recall", params=params, timeout=2.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Daemon error: {str(e)}")

@app.post("/snapshot")
async def snapshot_state(thread_id: str = Query("default")):
    """
    Requests the Rust daemon to flush the specific thread state to disk.
    """
    try:
        response = requests.post(f"{NULLD_URL}/snapshot", params={"thread_id": thread_id}, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Daemon error: {str(e)}")

@app.post("/restore")
async def restore_state(thread_id: str = Query("default")):
    """
    Requests the Rust daemon to load the specific thread state from disk.
    """
    try:
        response = requests.post(f"{NULLD_URL}/restore", params={"thread_id": thread_id}, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Daemon error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 to allow docker-compose cross-container communication
    uvicorn.run(app, host="0.0.0.0", port=8000)
