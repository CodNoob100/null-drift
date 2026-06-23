use axum::{
    Json, Router,
    extract::{DefaultBodyLimit, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
};

use moka::future::Cache;
use ndarray::Array1;
use null_drift_core::amn::AttractorIndex;
use null_drift_core::hrsa::Hrsa;
use null_drift_core::spl::Projector;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::fs;
use tokio::sync::RwLock;

#[derive(thiserror::Error, Debug)]
pub enum DaemonError {
    #[error("Failed to acquire lock")]
    LockError,
    #[error("Serialization/Deserialization failed: {0}")]
    PostcardError(#[from] postcard::Error),
    #[error("IO Error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Invalid embedding dimension")]
    InvalidDimension,
}

impl IntoResponse for DaemonError {
    fn into_response(self) -> axum::response::Response {
        let (status, err_msg) = match self {
            DaemonError::InvalidDimension => (StatusCode::BAD_REQUEST, self.to_string()),
            _ => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
        };
        (status, Json(SimpleResponse { status: err_msg })).into_response()
    }
}

#[derive(Serialize, Deserialize)]
struct ThreadState {
    amn: AttractorIndex,
    hrsa: Hrsa,
}

struct GlobalState {
    projectors: RwLock<HashMap<usize, Arc<Projector>>>,
    threads: Cache<String, Arc<RwLock<ThreadState>>>,
    cleanup_threshold: usize,
}

type SharedState = Arc<GlobalState>;

#[derive(Deserialize)]
struct ThreadQuery {
    #[serde(default = "default_thread_id")]
    thread_id: String,
}

fn default_thread_id() -> String {
    "default".to_string()
}

#[derive(Deserialize)]
struct InjectPayload {
    text: String,
    embedding: Vec<f32>,
    salience: f32,
}

#[derive(Serialize)]
struct InjectResponse {
    status: String,
    step: usize,
}

#[derive(Deserialize)]
struct RecallQuery {
    #[serde(default = "default_thread_id")]
    thread_id: String,
    steps_ago: Option<usize>,
}

#[derive(Serialize)]
struct RecallResponse {
    recovered_text: Option<String>,
}

#[derive(Serialize)]
struct SimpleResponse {
    status: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Starting null-drift HRSA multi-tenant daemon...");

    let eviction_listener = |key: Arc<String>,
                             value: Arc<RwLock<ThreadState>>,
                             _cause: moka::notification::RemovalCause| {
        let thread_id = key.to_string();
        tokio::spawn(async move {
            let ts = value.read().await;
            if let Ok(bytes) = postcard::to_stdvec(&*ts) {
                let _ = tokio::fs::write(format!("state_{}.nd", thread_id), bytes).await;
                println!(
                    "Disk Paging: Saved {} to disk due to inactivity.",
                    thread_id
                );
            }
        });
    };

    let cache = Cache::builder()
        .time_to_idle(Duration::from_secs(86400)) // 24 hours TTL
        .max_capacity(10000)
        .eviction_listener(eviction_listener)
        .build();

    let mut projectors = HashMap::new();
    projectors.insert(384, Arc::new(Projector::new(384, 10000)));

    let cleanup_threshold = std::env::var("CLEANUP_THRESHOLD")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(3000);

    let global_state = GlobalState {
        projectors: RwLock::new(projectors),
        threads: cache,
        cleanup_threshold,
    };

    let state = Arc::new(global_state);

    let app = Router::new()
        .route("/health", get(handle_health))
        .route("/inject", post(handle_inject))
        .route("/recall", get(handle_recall))
        .route("/snapshot", post(handle_snapshot))
        .route("/restore", post(handle_restore))
        .layer(DefaultBodyLimit::max(64 * 1024))
        .with_state(state);

    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string());
    let host = std::env::var("HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let bind_addr = format!("{}:{}", host, port);

    println!("Daemon listening on http://{}", bind_addr);
    let listener = tokio::net::TcpListener::bind(bind_addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

async fn handle_health() -> impl IntoResponse {
    (
        StatusCode::OK,
        Json(SimpleResponse {
            status: "ok".to_string(),
        }),
    )
}

async fn get_or_load_thread(
    state: &SharedState,
    thread_id: &str,
) -> Result<Arc<RwLock<ThreadState>>, DaemonError> {
    if let Some(ts) = state.threads.get(thread_id).await {
        return Ok(ts);
    }

    let file_path = format!("state_{}.nd", thread_id);
    if fs::metadata(&file_path).await.is_ok() {
        let bytes = fs::read(&file_path).await?;
        if let Ok(ts_data) = postcard::from_bytes::<ThreadState>(&bytes) {
            let ts = Arc::new(RwLock::new(ts_data));
            state
                .threads
                .insert(thread_id.to_string(), ts.clone())
                .await;
            return Ok(ts);
        }
    }

    let new_ts = ThreadState {
        amn: AttractorIndex::new(state.cleanup_threshold),
        hrsa: Hrsa::new(10000),
    };
    let ts = Arc::new(RwLock::new(new_ts));
    state
        .threads
        .insert(thread_id.to_string(), ts.clone())
        .await;
    Ok(ts)
}

async fn handle_inject(
    State(state): State<SharedState>,
    Query(query): Query<ThreadQuery>,
    Json(payload): Json<InjectPayload>,
) -> Result<impl IntoResponse, DaemonError> {
    let dim = payload.embedding.len();
    if dim == 0 {
        return Err(DaemonError::InvalidDimension);
    }

    let projector = {
        let read_guard = state.projectors.read().await;
        if let Some(p) = read_guard.get(&dim) {
            Arc::clone(p)
        } else {
            drop(read_guard);
            let mut write_guard = state.projectors.write().await;
            Arc::clone(write_guard.entry(dim).or_insert_with(|| {
                println!("Dynamically instantiating projector for dimension: {}", dim);
                Arc::new(Projector::new(dim, 10000))
            }))
        }
    };

    let thread_lock = get_or_load_thread(&state, &query.thread_id).await?;
    let mut ts = thread_lock.write().await;

    let dense_emb = Array1::from_vec(payload.embedding);
    let bipolar_event = projector.project_to_hypervector(dense_emb);

    if payload.salience >= 0.90 {
        ts.amn.store(bipolar_event.clone(), payload.text.clone());
    }

    ts.hrsa.inject_event(&bipolar_event, payload.salience);

    let current_step = ts.hrsa.step;

    Ok((
        StatusCode::OK,
        Json(InjectResponse {
            status: "success".to_string(),
            step: current_step,
        }),
    ))
}

async fn handle_recall(
    State(state): State<SharedState>,
    Query(query): Query<RecallQuery>,
) -> Result<impl IntoResponse, DaemonError> {
    let thread_lock = get_or_load_thread(&state, &query.thread_id).await?;
    let ts = thread_lock.read().await;

    let mut best_text = None;

    if let Some(steps) = query.steps_ago {
        if steps < ts.hrsa.step {
            let noisy_hv = ts.hrsa.recall_event(steps);
            if let Some(text) = ts.amn.cleanup(&noisy_hv) {
                best_text = Some(text);
            }
        }
    } else {
        // O(1) Recall: Find the dominant attractor in the current state without looping back in time!
        let noisy_hv: Vec<f32> = ts
            .hrsa
            .active_state
            .iter()
            .map(|&x| if x >= 0.0 { 1.0 } else { -1.0 })
            .collect();
        let mut local_min_hamming = usize::MAX;

        for (clean_hv, concept) in &ts.amn.attractors {
            let mut hamming = 0;
            for i in 0..noisy_hv.len() {
                if noisy_hv[i] != clean_hv[i] {
                    hamming += 1;
                }
            }
            if hamming < local_min_hamming {
                local_min_hamming = hamming;
                best_text = Some(concept.clone());
            }
        }
    }

    Ok((
        StatusCode::OK,
        Json(RecallResponse {
            recovered_text: best_text,
        }),
    ))
}

async fn handle_snapshot(
    State(state): State<SharedState>,
    Query(query): Query<ThreadQuery>,
) -> Result<impl IntoResponse, DaemonError> {
    let thread_lock = get_or_load_thread(&state, &query.thread_id).await?;
    let ts = thread_lock.read().await;

    let bytes = postcard::to_stdvec(&*ts)?;
    fs::write(format!("state_{}.nd", query.thread_id), &bytes).await?;

    Ok((
        StatusCode::OK,
        Json(SimpleResponse {
            status: "snapshot_saved".to_string(),
        }),
    ))
}

async fn handle_restore(
    State(state): State<SharedState>,
    Query(query): Query<ThreadQuery>,
) -> Result<impl IntoResponse, DaemonError> {
    let file_path = format!("state_{}.nd", query.thread_id);
    if fs::metadata(&file_path).await.is_ok() {
        let bytes = fs::read(&file_path).await?;
        let ts_data: ThreadState = postcard::from_bytes(&bytes)?;

        // Force overwrite in moka cache
        let ts = Arc::new(RwLock::new(ts_data));
        state.threads.insert(query.thread_id.clone(), ts).await;

        Ok((
            StatusCode::OK,
            Json(SimpleResponse {
                status: "restored".to_string(),
            }),
        ))
    } else {
        Ok((
            StatusCode::NOT_FOUND,
            Json(SimpleResponse {
                status: "state file not found".to_string(),
            }),
        ))
    }
}
