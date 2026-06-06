use ndarray::Array1;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct Hrsa {
    pub active_state: Array1<f32>,
    pub dimensions: usize,
    pub step: usize,
}

impl Hrsa {
    pub fn new(dimensions: usize) -> Self {
        Self {
            active_state: Array1::zeros(dimensions),
            dimensions,
            step: 0,
        }
    }

    /// Shift right (permute)
    pub fn permute(v: &Array1<f32>) -> Array1<f32> {
        let mut out = Array1::zeros(v.raw_dim());
        let d = v.len();
        for i in 0..d {
            out[(i + 1) % d] = v[i];
        }
        out
    }

    /// Shift left (inverse permute)
    pub fn inverse_permute(v: &Array1<f32>) -> Array1<f32> {
        let mut out = Array1::zeros(v.raw_dim());
        let d = v.len();
        for i in 0..d {
            out[i] = v[(i + 1) % d];
        }
        out
    }

    /// Superpose event weighted by salience into active_state
    pub fn inject_event(&mut self, bipolar_event: &Array1<f32>, salience: f32) {
        self.active_state = Self::permute(&self.active_state);
        self.active_state = &self.active_state + &(bipolar_event * salience);
        self.step += 1;
    }

    /// Unroll state to recover event from `steps_ago` and apply signum function to binarize
    pub fn recall_event(&self, steps_ago: usize) -> Array1<f32> {
        let mut query = self.active_state.clone();
        for _ in 0..steps_ago {
            query = Self::inverse_permute(&query);
        }
        // Binarize
        query.mapv(|x| if x >= 0.0 { 1.0 } else { -1.0 })
    }
}
