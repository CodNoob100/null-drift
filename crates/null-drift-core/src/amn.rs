use ndarray::Array1;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct AttractorIndex {
    pub attractors: Vec<(Array1<f32>, String)>,
    pub cleanup_threshold: usize, // Hamming distance threshold
}

impl AttractorIndex {
    pub fn new(cleanup_threshold: usize) -> Self {
        Self {
            attractors: Vec::new(),
            cleanup_threshold,
        }
    }

    pub fn store(&mut self, hypervector: Array1<f32>, semantic_text: String) {
        self.attractors.push((hypervector, semantic_text));
    }

    pub fn cleanup(&self, noisy_vec: &Array1<f32>) -> Option<String> {
        let mut best_match = None;
        let mut best_hamming = usize::MAX;

        for (attractor, text) in &self.attractors {
            let hamming = hamming_distance(noisy_vec, attractor);
            if hamming < best_hamming {
                best_hamming = hamming;
                best_match = Some(text.clone());
            }
        }

        if best_hamming <= self.cleanup_threshold {
            best_match
        } else {
            None
        }
    }
}

pub fn hamming_distance(a: &Array1<f32>, b: &Array1<f32>) -> usize {
    a.iter().zip(b.iter()).filter(|(x, y)| x != y).count()
}
