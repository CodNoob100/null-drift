use ndarray::{Array1, Array2};
use rand::SeedableRng;
use rand_distr::{Distribution, StandardNormal};
use rand_pcg::Pcg64;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone)]
pub struct Projector {
    pub w_proj: Array2<f32>,
}

impl Projector {
    pub fn new(dense_dim: usize, hyper_dim: usize) -> Self {
        let scale = 1.0 / (dense_dim as f32).sqrt();
        let mut w_proj = Array2::zeros((dense_dim, hyper_dim));
        let mut rng = Pcg64::seed_from_u64(42);
        for i in 0..dense_dim {
            for j in 0..hyper_dim {
                let val: f32 = StandardNormal.sample(&mut rng);
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

#[cfg(test)]
mod compatibility_tests {
    use super::Projector;
    use rand_distr05::{
        Distribution as LegacyDistribution, StandardNormal as LegacyStandardNormal,
    };
    use rand_pcg09::Pcg64 as LegacyPcg64;

    #[test]
    fn seeded_projection_matches_previous_rng_versions() {
        let projector = Projector::new(3, 8);
        let mut legacy_rng = <LegacyPcg64 as rand09::SeedableRng>::seed_from_u64(42);
        let scale = 1.0 / (3.0_f32).sqrt();

        for i in 0..3 {
            for j in 0..8 {
                let value: f32 = LegacyStandardNormal.sample(&mut legacy_rng);
                assert_eq!(
                    projector.w_proj[[i, j]],
                    value * scale,
                    "seeded projector drifted at [{i}, {j}]"
                );
            }
        }
    }
}
