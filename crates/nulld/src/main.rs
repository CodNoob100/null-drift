mod identity_ledger;

use axum::{
    Json, Router,
    extract::{DefaultBodyLimit, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
};

use identity_ledger::IdentityLedger;
use moka::future::Cache;
use ndarray::Array1;
use null_drift_core::amn::AttractorIndex;
use null_drift_core::hrsa::Hrsa;
use null_drift_core::spl::Projector;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;
use tokio::fs;
use tokio::io::AsyncWriteExt;
use tokio::sync::RwLock;

static NEXT_SNAPSHOT_ID: AtomicU64 = AtomicU64::new(0);

/// Write beside the previous checkpoint and rename only after writing all bytes.
async fn persist_snapshot(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    let number = NEXT_SNAPSHOT_ID.fetch_add(1, Ordering::Relaxed);
    let temp_path = path.with_extension(format!("nd.{}.{}.tmp", std::process::id(), number));

    let result = async {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp_path)
            .await?;
        file.write_all(bytes).await?;
        file.sync_all().await?;
        drop(file);
        fs::rename(&temp_path, path).await
    }
    .await;

    if result.is_err() {
        let _ = fs::remove_file(&temp_path).await;
    }
    result
}

const HYPERVECTOR_DIM: usize = 10_000;
const MAX_EMBEDDING_DIM: usize = 4_096;
// 64 million f32 entries = 256 MB for all cached projection matrices combined.
const MAX_PROJECTOR_ELEMENTS: usize = 64_000_000;

fn projector_budget_allows(
    mut cached_dimensions: impl Iterator<Item = usize>,
    requested_dimension: usize,
) -> bool {
    if requested_dimension == 0 || requested_dimension > MAX_EMBEDDING_DIM {
        return false;
    }

    cached_dimensions
        .try_fold(requested_dimension, |sum, dim| sum.checked_add(dim))
        .and_then(|sum| sum.checked_mul(HYPERVECTOR_DIM))
        .is_some_and(|elements| elements <= MAX_PROJECTOR_ELEMENTS)
}

#[derive(thiserror::Error, Debug)]
pub enum DaemonError {
    #[error("Failed to acquire lock")]
    LockError,
    #[error("Serialization/Deserialization failed: {0}")]
    PostcardError(#[from] postcard::Error),
    #[error("IO Error: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Thread initialization failed: {0}")]
    ThreadInitialization(String),
    #[error("Invalid embedding dimension (expected 1 to 4096 floats)")]
    InvalidDimension,
    #[error("Projection matrix budget exhausted; reuse an existing embedding dimension")]
    ProjectorBudgetExceeded,
    #[error(
        "Invalid thread ID: expected 1–128 ASCII letters, digits, '-', '_' or '.' without '..'"
    )]
    InvalidThreadId,
}

impl IntoResponse for DaemonError {
    fn into_response(self) -> axum::response::Response {
        let (status, err_msg) = match self {
            DaemonError::InvalidDimension | DaemonError::InvalidThreadId => {
                (StatusCode::BAD_REQUEST, self.to_string())
            }
            DaemonError::ProjectorBudgetExceeded => {
                (StatusCode::SERVICE_UNAVAILABLE, self.to_string())
            }
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
    identity: RwLock<IdentityLedger>,
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

fn validate_thread_id(thread_id: &str) -> Result<(), DaemonError> {
    if thread_id.is_empty()
        || thread_id.len() > 128
        || thread_id == "."
        || thread_id.contains("..")
        || !thread_id
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_' | b'.'))
    {
        return Err(DaemonError::InvalidThreadId);
    }

    Ok(())
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

#[derive(Deserialize)]
struct MemoryRequest {
    operation: String,
    namespace: Vec<String>,
    #[serde(default)]
    key: String,
    value: Option<serde_json::Value>,
    #[serde(default)]
    offset: usize,
    #[serde(default = "default_memory_limit")]
    limit: usize,
}

const FRAMEWORK_MEMORY_SNAPSHOT: &str = "framework_memory.nd";

async fn load_identity_ledger() -> std::io::Result<IdentityLedger> {
    match fs::read(FRAMEWORK_MEMORY_SNAPSHOT).await {
        Ok(bytes) => postcard::from_bytes(&bytes).map_err(|error| {
            std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("Cannot decode framework memory snapshot: {error}"),
            )
        }),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            Ok(IdentityLedger::default())
        }
        Err(error) => Err(error),
    }
}

fn default_memory_limit() -> usize {
    100
}

async fn handle_memory(
    State(state): State<SharedState>,
    Json(request): Json<MemoryRequest>,
) -> impl IntoResponse {
    let mut ledger = state.identity.write().await;
    let result = match request.operation.as_str() {
        "put" => match request.value {
            Some(value) => ledger
                .put(&request.namespace, &request.key, value)
                .map(|revision| serde_json::json!({"revision": revision})),
            None => return (StatusCode::BAD_REQUEST, Json(serde_json::json!({"error": "value required"}))),
        },
        "get" => Ok(serde_json::json!({"record": ledger.get(&request.namespace, &request.key)})),
        "delete" => ledger
            .delete(&request.namespace, &request.key)
            .map(|deleted| serde_json::json!({"deleted": deleted})),
        "search" => Ok(serde_json::json!({"records": ledger.search(&request.namespace, request.offset, request.limit)})),
        "namespaces" => Ok(serde_json::json!({"namespaces": ledger.namespaces(&request.namespace)})),
        _ => return (StatusCode::BAD_REQUEST, Json(serde_json::json!({"error": "unknown operation"}))),
    };
    match result {
        Ok(value) => {
            if request.operation == "put" || request.operation == "delete" {
                let bytes = match postcard::to_stdvec(&*ledger) {
                    Ok(bytes) => bytes,
                    Err(_) => return (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Json(serde_json::json!({"error": "memory serialization failed"})),
                    ),
                };
                if persist_snapshot(Path::new(FRAMEWORK_MEMORY_SNAPSHOT), &bytes)
                    .await
                    .is_err()
                {
                    return (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        Json(serde_json::json!({"error": "memory snapshot failed"})),
                    );
                }
            }
            (StatusCode::OK, Json(value))
        }
        Err(error) => (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"error": format!("{error:?}")})),
        ),
    }
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
                let path = format!("state_{}.nd", thread_id);
                match persist_snapshot(Path::new(&path), &bytes).await {
                    Ok(()) => println!(
                        "Disk Paging: Saved {} to disk due to inactivity.",
                        thread_id
                    ),
                    Err(error) => eprintln!(
                        "Disk Paging: Failed to save {} due to: {}",
                        thread_id, error
                    ),
                }
            }
        });
    };

    let cache = Cache::builder()
        .time_to_idle(Duration::from_secs(86400)) // 24 hours TTL
        .max_capacity(10000)
        .eviction_listener(eviction_listener)
        .build();

    let mut projectors = HashMap::new();
    projectors.insert(384, Arc::new(Projector::new(384, HYPERVECTOR_DIM)));

    let cleanup_threshold = std::env::var("CLEANUP_THRESHOLD")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(3000);

    let global_state = GlobalState {
        projectors: RwLock::new(projectors),
        threads: cache,
        cleanup_threshold,
        identity: RwLock::new(load_identity_ledger().await?),
    };

    let state = Arc::new(global_state);

    let app = Router::new()
        .route("/health", get(handle_health))
        .route("/inject", post(handle_inject))
        .route("/recall", get(handle_recall))
        .route("/snapshot", post(handle_snapshot))
        .route("/restore", post(handle_restore))
        .route("/memory", post(handle_memory))
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

/// Load a checkpoint or initialize only if no checkpoint exists.
/// Invalid and unreadable existing files must never become blank threads.
async fn load_thread_from_path(
    path: &Path,
    cleanup_threshold: usize,
) -> std::io::Result<Arc<RwLock<ThreadState>>> {
    match fs::read(path).await {
        Ok(bytes) => {
            let data = postcard::from_bytes::<ThreadState>(&bytes).map_err(|error| {
                std::io::Error::new(
                    std::io::ErrorKind::InvalidData,
                    format!("Cannot decode existing thread snapshot: {error}"),
                )
            })?;
            Ok(Arc::new(RwLock::new(data)))
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            Ok(Arc::new(RwLock::new(ThreadState {
                amn: AttractorIndex::new(cleanup_threshold),
                hrsa: Hrsa::new(HYPERVECTOR_DIM),
            })))
        }
        Err(error) => Err(error),
    }
}

async fn get_or_load_thread(
    state: &SharedState,
    thread_id: &str,
) -> Result<Arc<RwLock<ThreadState>>, DaemonError> {
    validate_thread_id(thread_id)?;

    // Only one future may hydrate or create a missing thread for each key.
    // Previously concurrent misses could each create a different ThreadState
    // and overwrite each other in the cache, losing accepted events.
    let file_path = format!("state_{}.nd", thread_id);
    let cleanup_threshold = state.cleanup_threshold;
    state
        .threads
        .try_get_with(thread_id.to_string(), async move {
            load_thread_from_path(Path::new(&file_path), cleanup_threshold).await
        })
        .await
        .map_err(|err| DaemonError::ThreadInitialization(err.to_string()))
}

async fn handle_inject(
    State(state): State<SharedState>,
    Query(query): Query<ThreadQuery>,
    Json(payload): Json<InjectPayload>,
) -> Result<impl IntoResponse, DaemonError> {
    // Validate all cheap request properties before allocating a new matrix.
    validate_thread_id(&query.thread_id)?;
    let dim = payload.embedding.len();
    if dim == 0 || dim > MAX_EMBEDDING_DIM {
        return Err(DaemonError::InvalidDimension);
    }

    let projector = {
        let read_guard = state.projectors.read().await;
        if let Some(p) = read_guard.get(&dim) {
            Arc::clone(p)
        } else {
            drop(read_guard);
            let mut write_guard = state.projectors.write().await;
            // Re-check the key after acquiring the write lock, because another
            // request may have created the same projector in the meantime.
            if !write_guard.contains_key(&dim)
                && !projector_budget_allows(write_guard.keys().copied(), dim)
            {
                return Err(DaemonError::ProjectorBudgetExceeded);
            }
            Arc::clone(write_guard.entry(dim).or_insert_with(|| {
                println!("Dynamically instantiating projector for dimension: {}", dim);
                Arc::new(Projector::new(dim, HYPERVECTOR_DIM))
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

fn cleanup_current_state(state: &ThreadState) -> Option<String> {
    let bipolar = state
        .hrsa
        .active_state
        .mapv(|value| if value >= 0.0 { 1.0 } else { -1.0 });
    state.amn.cleanup(&bipolar)
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
        // Apply the same cleanup threshold and dimension-safe distance that
        // historical recall uses; the nearest unrelated anchor is not a hit.
        best_text = cleanup_current_state(&ts);
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
    let path = format!("state_{}.nd", query.thread_id);
    persist_snapshot(Path::new(&path), &bytes).await?;

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
    validate_thread_id(&query.thread_id)?;

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

#[cfg(test)]
mod tests {
    use super::{
        GlobalState, SharedState, ThreadState, cleanup_current_state, get_or_load_thread,
        load_thread_from_path, persist_snapshot, projector_budget_allows, validate_thread_id,
    };
    use moka::future::Cache;
    use ndarray::Array1;
    use null_drift_core::amn::AttractorIndex;
    use null_drift_core::hrsa::Hrsa;
    use std::collections::HashMap;
    use std::sync::Arc;
    use tokio::sync::{Barrier, RwLock};

    #[tokio::test]
    async fn damaged_checkpoint_does_not_create_empty_state() {
        let id = super::NEXT_SNAPSHOT_ID.fetch_add(1, super::Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "nulld_corrupt_snapshot_{}_{}.nd",
            std::process::id(),
            id
        ));
        tokio::fs::write(&path, b"").await.unwrap();

        let error = match load_thread_from_path(&path, 3000).await {
            Ok(_) => panic!("corrupt checkpoint was silently replaced"),
            Err(error) => error,
        };
        assert_eq!(error.kind(), std::io::ErrorKind::InvalidData);
        assert_eq!(tokio::fs::read(&path).await.unwrap(), b"");
        tokio::fs::remove_file(path).await.unwrap();
    }

    #[tokio::test]
    async fn valid_checkpoint_is_loaded_without_reset() {
        let id = super::NEXT_SNAPSHOT_ID.fetch_add(1, super::Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "nulld_valid_snapshot_{}_{}.nd",
            std::process::id(),
            id
        ));
        let mut state = ThreadState {
            amn: AttractorIndex::new(3000),
            hrsa: Hrsa::new(4),
        };
        state.hrsa.step = 17;
        let bytes = postcard::to_stdvec(&state).unwrap();
        tokio::fs::write(&path, bytes).await.unwrap();
        let loaded = load_thread_from_path(&path, 3000).await.unwrap();
        assert_eq!(loaded.read().await.hrsa.step, 17);
        tokio::fs::remove_file(path).await.unwrap();
    }

    #[tokio::test]
    async fn missing_checkpoint_creates_fresh_state() {
        let id = super::NEXT_SNAPSHOT_ID.fetch_add(1, super::Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "nulld_absent_snapshot_{}_{}.nd",
            std::process::id(),
            id
        ));
        assert!(!path.exists());
        let loaded = load_thread_from_path(&path, 3000).await.unwrap();
        assert_eq!(loaded.read().await.hrsa.step, 0);
        assert_eq!(loaded.read().await.hrsa.active_state.len(), 10_000);
        assert!(!path.exists());
    }

    #[test]
    fn current_recall_rejects_unrelated_and_truncated_anchors() {
        let mut state = ThreadState {
            amn: AttractorIndex::new(1),
            hrsa: Hrsa::new(4),
        };
        state.hrsa.active_state = Array1::from_vec(vec![2.0, 3.0, 4.0, 5.0]);
        state.amn.store(
            Array1::from_vec(vec![-1.0, -1.0, -1.0, -1.0]),
            "unrelated".to_string(),
        );
        state
            .amn
            .store(Array1::from_vec(vec![1.0, 1.0]), "short".to_string());
        assert_eq!(cleanup_current_state(&state), None);

        state.amn.store(
            Array1::from_vec(vec![1.0, 1.0, 1.0, 1.0]),
            "matching".to_string(),
        );
        assert_eq!(cleanup_current_state(&state), Some("matching".to_string()));
    }

    #[test]
    fn current_recall_returns_none_without_attractors() {
        let state = ThreadState {
            amn: AttractorIndex::new(3000),
            hrsa: Hrsa::new(4),
        };
        assert_eq!(cleanup_current_state(&state), None);
    }

    #[tokio::test]
    async fn concurrent_first_access_shares_a_single_thread_state() {
        let state: SharedState = Arc::new(GlobalState {
            projectors: RwLock::new(HashMap::new()),
            threads: Cache::new(64),
            cleanup_threshold: 3000,
            identity: RwLock::new(IdentityLedger::default()),
        });
        let id = super::NEXT_SNAPSHOT_ID.fetch_add(1, super::Ordering::Relaxed);
        let thread_id = format!("coalesce_{}_{}", std::process::id(), id);
        let count = 24;
        let barrier = Arc::new(Barrier::new(count + 1));
        let mut requests = Vec::new();

        for _ in 0..count {
            let state = Arc::clone(&state);
            let barrier = Arc::clone(&barrier);
            let thread_id = thread_id.clone();
            requests.push(tokio::spawn(async move {
                barrier.wait().await;
                get_or_load_thread(&state, &thread_id).await.unwrap()
            }));
        }

        barrier.wait().await;
        let first = requests.remove(0).await.unwrap();
        for request in requests {
            let loaded = request.await.unwrap();
            assert!(Arc::ptr_eq(&first, &loaded));
        }

        // All callers must update the same state rather than discarded copies.
        first.write().await.hrsa.step = 7;
        let reloaded = get_or_load_thread(&state, &thread_id).await.unwrap();
        assert_eq!(reloaded.read().await.hrsa.step, 7);
    }

    #[tokio::test]
    async fn distinct_thread_ids_have_distinct_state() {
        let state: SharedState = Arc::new(GlobalState {
            projectors: RwLock::new(HashMap::new()),
            threads: Cache::new(64),
            cleanup_threshold: 3000,
            identity: RwLock::new(IdentityLedger::default()),
        });
        let id = super::NEXT_SNAPSHOT_ID.fetch_add(1, super::Ordering::Relaxed);
        let a = format!("thread_a_{}_{}", std::process::id(), id);
        let b = format!("thread_b_{}_{}", std::process::id(), id);
        let ta = get_or_load_thread(&state, &a).await.unwrap();
        let tb = get_or_load_thread(&state, &b).await.unwrap();
        assert!(!Arc::ptr_eq(&ta, &tb));
    }

    #[tokio::test]
    async fn checkpoint_replace_is_complete_and_atomic() {
        let id = super::NEXT_SNAPSHOT_ID.fetch_add(1, super::Ordering::Relaxed);
        let path = std::env::temp_dir().join(format!(
            "nulld_snapshot_test_{}_{}.nd",
            std::process::id(),
            id
        ));
        let old = b"previous-complete-checkpoint";
        let new = b"replacement-complete-checkpoint";
        persist_snapshot(&path, old).await.unwrap();
        assert_eq!(tokio::fs::read(&path).await.unwrap(), old);
        persist_snapshot(&path, new).await.unwrap();
        assert_eq!(tokio::fs::read(&path).await.unwrap(), new);
        tokio::fs::remove_file(&path).await.unwrap();
    }

    #[tokio::test]
    async fn invalid_snapshot_destination_does_not_create_target_file() {
        let id = super::NEXT_SNAPSHOT_ID.fetch_add(1, super::Ordering::Relaxed);
        let path = std::env::temp_dir()
            .join(format!(
                "nulld_missing_directory_{}_{}",
                std::process::id(),
                id
            ))
            .join("state.nd");
        assert!(persist_snapshot(&path, b"invalid").await.is_err());
        assert!(!path.exists());
    }

    #[test]
    fn projector_budget_accepts_normal_embedding_dimensions() {
        assert!(projector_budget_allows([].into_iter(), 384));
        assert!(projector_budget_allows([384].into_iter(), 768));
        assert!(projector_budget_allows([384].into_iter(), 4096));
        assert!(projector_budget_allows([384, 3072].into_iter(), 1536));
    }

    #[test]
    fn projector_budget_rejects_large_or_excessive_allocations() {
        assert!(!projector_budget_allows([].into_iter(), 0));
        assert!(!projector_budget_allows([].into_iter(), 4097));
        assert!(!projector_budget_allows([384, 4096].into_iter(), 2048));
        assert!(!projector_budget_allows([6144].into_iter(), 257));
        assert!(projector_budget_allows([6144].into_iter(), 256));
        assert!(!projector_budget_allows([usize::MAX].into_iter(), 1));
    }

    #[test]
    fn accepts_safe_thread_ids() {
        for id in [
            "default",
            "agent_007",
            "test_langgraph_agent1",
            "tenant-1",
            "agent.v2",
        ] {
            assert!(
                validate_thread_id(id).is_ok(),
                "rejected valid thread ID: {id}"
            );
        }
    }

    #[test]
    fn rejects_unsafe_thread_ids() {
        for id in [
            "",
            ".",
            "..",
            "../escape",
            "a/../b",
            "a/b",
            "a\\b",
            "with space",
            "a\nb",
        ] {
            assert!(
                validate_thread_id(id).is_err(),
                "accepted unsafe thread ID: {id:?}"
            );
        }
        assert!(validate_thread_id(&"a".repeat(129)).is_err());
    }
}
