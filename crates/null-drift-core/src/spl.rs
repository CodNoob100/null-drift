use ndarray::{Array1, Array2};
use rand::Rng;
use rand_distr::StandardNormal;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone)]
pub struct Projector {
    pub w_proj: Array2<f32>,
}

impl Projector {
    pub fn new(dense_dim: usize, hyper_dim: usize) -> Self {
        let scale = 1.0 / (dense_dim as f32).sqrt();
        let mut w_proj = Array2::zeros((dense_dim, hyper_dim));
        let mut rng = rand::thread_rng();
        for i in 0..dense_dim {
            for j in 0..hyper_dim {
                let val: f32 = rng.sample(StandardNormal);
                w_proj[[i, j]] = val * scale;
            }
        }

        Self { w_proj }
    }

    pub fn project_to_hypervector(&self, dense: Array1<f32>) -> Array1<f32> {
        let projected = dense.dot(&self.w_proj);

        // Bipolar activation
        projected.mapv(|x| if x >= 0.0 { 1.0 } else { -1.0 })
    }
}
