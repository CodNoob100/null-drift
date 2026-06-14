use axum::{
    extract::{Query, State},
    http::{header, StatusCode},
    response::Response,
    routing::{get, post},
    Json, Router,
};
use fastembed::{InitOptions, TextEmbedding};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicUsize, Ordering};

#[derive(Clone)]
struct AppState {
    embedders: Arc<Vec<Mutex<TextEmbedding>>>,
    index: Arc<AtomicUsize>,
    client: Client,
    nulld_url: String,
}

#[derive(Deserialize)]
struct ThreadQuery {
    #[serde(default = "default_thread_id")]
    thread_id: String,
}

#[derive(Deserialize)]
struct RecallQuery {
    #[serde(default = "default_thread_id")]
    thread_id: String,
    steps_ago: Option<usize>,
}

fn default_thread_id() -> String {
    "default".to_string()
}

#[derive(Deserialize)]
struct TextRequest {
    text: String,
    salience: f32,
}

#[derive(Serialize)]
struct DaemonPayload {
    text: String,
    embedding: Vec<f32>,
    salience: f32,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let num_models = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(4);
    println!("Loading {} fastembed models for concurrency...", num_models);
    
    let mut models = Vec::new();
    for _ in 0..num_models {
        models.push(Mutex::new(TextEmbedding::try_new(InitOptions::new(fastembed::EmbeddingModel::AllMiniLML6V2))?));
    }

    let nulld_url =
        std::env::var("NULLD_URL").unwrap_or_else(|_| "http://127.0.0.1:3000".to_string());

    let state = AppState {
        embedders: Arc::new(models),
        index: Arc::new(AtomicUsize::new(0)),
        client: Client::new(),
        nulld_url,
    };

    let app = Router::new()
        .route("/inject", post(inject_memory))
        .route("/recall", get(recall_state))
        .route("/snapshot", post(snapshot_state))
        .route("/restore", post(restore_state))
        .with_state(state);

    let port = std::env::var("PORT").unwrap_or_else(|_| "8000".to_string());
    let host = std::env::var("HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let bind_addr = format!("{}:{}", host, port);

    println!("Gateway listening on http://{}", bind_addr);
    let listener = tokio::net::TcpListener::bind(bind_addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

fn build_json_response(status: reqwest::StatusCode, body: String) -> Response {
    Response::builder()
        .status(status)
        .header(header::CONTENT_TYPE, "application/json")
        .body(body.into())
        .unwrap()
}

async fn inject_memory(
    State(state): State<AppState>,
    Query(query): Query<ThreadQuery>,
    Json(payload): Json<TextRequest>,
) -> Result<Response, (StatusCode, String)> {
    let text = payload.text.clone();
    let embedders = state.embedders.clone();
    let idx = state.index.fetch_add(1, Ordering::Relaxed) % embedders.len();

    let embeddings = tokio::task::spawn_blocking(move || {
        let mut embedder = embedders[idx].lock().unwrap();
        embedder.embed(vec![&text], None)
    })
    .await
    .unwrap()
    .map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            format!("Embedding failed: {}", e),
        )
    })?;

    let embedding = embeddings.into_iter().next().unwrap();

    let daemon_payload = DaemonPayload {
        text: payload.text,
        embedding,
        salience: payload.salience,
    };

    let url = format!("{}/inject", state.nulld_url);
    let res = state
        .client
        .post(&url)
        .query(&[("thread_id", &query.thread_id)])
        .json(&daemon_payload)
        .send()
        .await
        .map_err(|e| (StatusCode::BAD_GATEWAY, e.to_string()))?;

    let status = res.status();
    let body = res.text().await.unwrap_or_default();
    Ok(build_json_response(status, body))
}

async fn recall_state(
    State(state): State<AppState>,
    Query(query): Query<RecallQuery>,
) -> Result<Response, (StatusCode, String)> {
    let url = format!("{}/recall", state.nulld_url);
    let mut req = state
        .client
        .get(&url)
        .query(&[("thread_id", &query.thread_id)]);
    if let Some(steps) = query.steps_ago {
        req = req.query(&[("steps_ago", &steps)]);
    }

    let res = req
        .send()
        .await
        .map_err(|e| (StatusCode::BAD_GATEWAY, e.to_string()))?;
    let status = res.status();
    let body = res.text().await.unwrap_or_default();
    Ok(build_json_response(status, body))
}

async fn snapshot_state(
    State(state): State<AppState>,
    Query(query): Query<ThreadQuery>,
) -> Result<Response, (StatusCode, String)> {
    let url = format!("{}/snapshot", state.nulld_url);
    let res = state
        .client
        .post(&url)
        .query(&[("thread_id", &query.thread_id)])
        .send()
        .await
        .map_err(|e| (StatusCode::BAD_GATEWAY, e.to_string()))?;
    let status = res.status();
    let body = res.text().await.unwrap_or_default();
    Ok(build_json_response(status, body))
}

async fn restore_state(
    State(state): State<AppState>,
    Query(query): Query<ThreadQuery>,
) -> Result<Response, (StatusCode, String)> {
    let url = format!("{}/restore", state.nulld_url);
    let res = state
        .client
        .post(&url)
        .query(&[("thread_id", &query.thread_id)])
        .send()
        .await
        .map_err(|e| (StatusCode::BAD_GATEWAY, e.to_string()))?;
    let status = res.status();
    let body = res.text().await.unwrap_or_default();
    Ok(build_json_response(status, body))
}
