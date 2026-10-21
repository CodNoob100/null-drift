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
        let dimensions = self.active_state.len();
        let mut recovered = Array1::zeros(self.active_state.raw_dim());

        if dimensions == 0 {
            return recovered;
        }

        // Multiple inverse permutations are equivalent to one cyclic offset.
        // Reduces recall from O(steps_ago * dimensions) to O(dimensions).
        let offset = steps_ago % dimensions;
        for i in 0..dimensions {
            let value = self.active_state[(i + offset) % dimensions];
            recovered[i] = if value >= 0.0 { 1.0 } else { -1.0 };
        }
        recovered
    }
}

#[cfg(test)]
mod tests {
    use super::Hrsa;
    use ndarray::Array1;

    #[test]
    fn recall_matches_repeated_inverse_permutations() {
        for dimensions in [0, 1, 3, 8, 17] {
            let mut state = Hrsa::new(dimensions);
            state.active_state =
                Array1::from_iter((0..dimensions).map(|i| i as f32 - dimensions as f32 / 2.0));

            for steps in [0, 1, 2, 7, 17, 31, 1000] {
                let mut expected = state.active_state.clone();
                for _ in 0..steps {
                    expected = Hrsa::inverse_permute(&expected);
                }
                let expected = expected.mapv(|x| if x >= 0.0 { 1.0 } else { -1.0 });
                assert_eq!(state.recall_event(steps), expected);
            }
        }
    }

    #[test]
    fn very_large_recall_step_count_wraps_correctly() {
        let mut state = Hrsa::new(5);
        state.active_state = Array1::from_vec(vec![-5.0, -1.0, 0.0, 1.0, 5.0]);
        assert_eq!(
            state.recall_event(usize::MAX),
            state.recall_event(usize::MAX % 5)
        );
    }
}
