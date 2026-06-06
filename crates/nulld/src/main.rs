use axum::{
    Json, Router,
    extract::{DefaultBodyLimit, Query, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
};
use bincode::Options;
use ndarray::{Array1, Array2};
use null_drift_core::amn::AttractorIndex;
use null_drift_core::hrsa::Hrsa;
use null_drift_core::spl::Projector;
use serde::{Deserialize, Serialize};
use std::fs;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(thiserror::Error, Debug)]
pub enum DaemonError {
    #[error("Failed to acquire lock")]
    LockError,
    #[error("Serialization/Deserialization failed: {0}")]
    BincodeError(#[from] bincode::Error),
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
struct CognitiveState {
    projector_matrix: Array2<f32>,
    active_state: Array1<f32>,
    step: usize,
    amn_attractors: Vec<(Array1<f32>, String)>,
    step_history: Vec<String>,
}

struct DaemonState {
    projector: Projector,
    amn: AttractorIndex,
    hrsa: Hrsa,
    step_history: Vec<String>,
}

type SharedState = Arc<RwLock<DaemonState>>;

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
    println!("Starting null-drift HRSA daemon configuration...");

    let state_file = "state.nd";
    let daemon_state = if fs::metadata(state_file).is_ok() {
        println!("Found checkpoint state.nd. Restoring...");
        let bytes = fs::read(state_file)?;

        // SECURITY: Bounded deserialization (50MB limit)
        let bincode_opts = bincode::DefaultOptions::new().with_limit(50 * 1024 * 1024);
        let cog_state: CognitiveState = bincode_opts.deserialize(&bytes)?;

        let mut hrsa = Hrsa::new(10000);
        hrsa.active_state = cog_state.active_state;
        hrsa.step = cog_state.step;

        DaemonState {
            projector: Projector {
                w_proj: cog_state.projector_matrix,
            },
            amn: AttractorIndex {
                attractors: cog_state.amn_attractors,
                cleanup_threshold: 3000,
            },
            hrsa,
            step_history: cog_state.step_history,
        }
    } else {
        println!("No checkpoint found. Generating fresh Gaussian W_proj...");
        DaemonState {
            projector: Projector::new(384, 10000),
            amn: AttractorIndex::new(3000),
            hrsa: Hrsa::new(10000),
            step_history: Vec::new(),
        }
    };

    // SECURITY: Use RwLock to prevent panics from poisoning the state
    let state = Arc::new(RwLock::new(daemon_state));

    let app = Router::new()
        .route("/inject", post(handle_inject))
        .route("/recall", get(handle_recall))
        .route("/snapshot", post(handle_snapshot))
        .route("/restore", post(handle_restore))
        // SECURITY: 64KB body limit to prevent memory exhaustion
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

async fn handle_inject(
    State(state): State<SharedState>,
    Json(payload): Json<InjectPayload>,
) -> Result<impl IntoResponse, DaemonError> {
    if payload.embedding.len() != 384 {
        return Err(DaemonError::InvalidDimension);
    }

    let dense_emb = Array1::from_vec(payload.embedding);

    // Acquire Write Lock
    let mut st = state.write().await;

    let bipolar_event = st.projector.project_to_hypervector(dense_emb);

    if payload.salience >= 0.90 {
        st.amn.store(bipolar_event.clone(), payload.text.clone());
    }

    st.hrsa.inject_event(&bipolar_event, payload.salience);
    st.step_history.push(payload.text.clone());

    let current_step = st.hrsa.step;

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
    // Acquire Read Lock (Highly concurrent)
    let st = state.read().await;

    let mut best_text = None;
    let mut best_score = 0.0;

    if let Some(steps) = query.steps_ago {
        if steps < st.step_history.len() {
            let noisy_hv = st.hrsa.recall_event(steps);
            if let Some(text) = st.amn.cleanup(&noisy_hv) {
                best_text = Some(text);
            }
        }
    } else {
        for steps in 0..st.step_history.len() {
            let noisy_hv = st.hrsa.recall_event(steps);
            let mut local_best = None;
            let mut local_min_hamming = usize::MAX;

            for (clean_hv, concept) in &st.amn.attractors {
                let mut hamming = 0;
                for i in 0..noisy_hv.len() {
                    if noisy_hv[i] != clean_hv[i] {
                        hamming += 1;
                    }
                }
                if hamming < local_min_hamming {
                    local_min_hamming = hamming;
                    local_best = Some(concept.clone());
                }
            }

            let similarity_score = 10000.0 - (local_min_hamming as f32);
            if similarity_score > best_score {
                best_score = similarity_score;
                best_text = local_best;
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
) -> Result<impl IntoResponse, DaemonError> {
    let st = state.read().await;
    let cog_state = CognitiveState {
        projector_matrix: st.projector.w_proj.clone(),
        active_state: st.hrsa.active_state.clone(),
        step: st.hrsa.step,
        amn_attractors: st.amn.attractors.clone(),
        step_history: st.step_history.clone(),
    };

    let bytes = bincode::serialize(&cog_state)?;
    fs::write("state.nd", &bytes)?;

    Ok((
        StatusCode::OK,
        Json(SimpleResponse {
            status: "snapshot_saved".to_string(),
        }),
    ))
}

async fn handle_restore(
    State(state): State<SharedState>,
) -> Result<impl IntoResponse, DaemonError> {
    if fs::metadata("state.nd").is_ok() {
        let bytes = fs::read("state.nd")?;
        let bincode_opts = bincode::DefaultOptions::new().with_limit(50 * 1024 * 1024);
        let cog_state: CognitiveState = bincode_opts.deserialize(&bytes)?;

        let mut st = state.write().await;
        st.projector.w_proj = cog_state.projector_matrix;
        st.hrsa.active_state = cog_state.active_state;
        st.hrsa.step = cog_state.step;
        st.amn.attractors = cog_state.amn_attractors;
        st.step_history = cog_state.step_history;

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
                status: "state.nd not found".to_string(),
            }),
        ))
    }
}
