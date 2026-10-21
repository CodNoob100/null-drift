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
    // zip compares only the common prefix. Count unmatched dimensions too.
    a.iter().zip(b.iter()).filter(|(x, y)| x != y).count() + a.len().abs_diff(b.len())
}

#[cfg(test)]
mod tests {
    use super::{AttractorIndex, hamming_distance};
    use ndarray::Array1;

    #[test]
    fn distance_counts_unpaired_dimensions() {
        let short = Array1::from_vec(vec![1.0, -1.0]);
        let long = Array1::from_vec(vec![1.0, -1.0, 1.0, -1.0]);
        assert_eq!(hamming_distance(&short, &long), 2);
        assert_eq!(hamming_distance(&long, &short), 2);
        assert_eq!(hamming_distance(&Array1::zeros(0), &long), 4);
    }

    #[test]
    fn cleanup_rejects_truncated_false_matches() {
        let mut index = AttractorIndex::new(0);
        index.store(Array1::from_vec(vec![1.0, -1.0]), "short".to_string());
        assert_eq!(index.cleanup(&Array1::from_vec(vec![1.0, -1.0, 1.0])), None);
        assert_eq!(
            index.cleanup(&Array1::from_vec(vec![1.0, -1.0])),
            Some("short".to_string())
        );
    }
}
