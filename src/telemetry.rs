use std::collections::VecDeque;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Regime {
    A, // Over-Compressed
    B, // Functional Cognition
    C, // Overstimulated
    D, // Reverberating
    E, // Chaotic
}

pub struct TelemetryTracker {
    history_attractors: VecDeque<usize>,
    history_norms: VecDeque<f32>,
    l4_failures: usize,
    same_attractor_count: usize,
    last_attractor: Option<usize>,
    jumps_in_window: usize,
    debug: bool,
}

impl TelemetryTracker {
    pub fn new(debug: bool) -> Self {
        Self {
            history_attractors: VecDeque::with_capacity(10001),
            history_norms: VecDeque::with_capacity(1001),
            l4_failures: 0,
            same_attractor_count: 0,
            last_attractor: None,
            jumps_in_window: 0,
            debug,
        }
    }

    pub fn update(&mut self, attractor: usize, norm: f32, sim: f32, _cycle: usize) -> Option<Regime> {
        if self.debug && _cycle % 500 == 0 {
            println!("[CYCLE {:>6}] Attractor: {:>2}, Sim: {:.4}, Norm: {:.4}, Jumps/10000: {:>4}, Same count: {:>4}", 
                _cycle, attractor, sim, norm, self.jumps_in_window, self.same_attractor_count);
        }

        // Region E: L4 Failure Tracking (Rolling 1000 window)
        let is_failure = !norm.is_finite() || norm > 1e6 || sim.is_nan() || sim.abs() < 1e-6;
        if is_failure {
            self.l4_failures += 1;
        }
        self.history_norms.push_back(if is_failure { 1.0 } else { 0.0 });
        if self.history_norms.len() > 1000 {
            if self.history_norms.pop_front() == Some(1.0) {
                self.l4_failures -= 1;
            }
        }
        if self.l4_failures > 10 {
            if self.debug { println!("--> Exiting Region E (Chaotic)"); }
            return Some(Regime::E);
        }

        // Jump Tracking for Region C & Region A
        let is_jump = Some(attractor) != self.last_attractor;
        if !is_jump {
            self.same_attractor_count += 1;
        } else {
            self.same_attractor_count = 0;
        }
        self.last_attractor = Some(attractor);

        // Region A: Over-compressed (Same attractor for 5000 cycles)
        if self.same_attractor_count >= 5000 {
            if self.debug { println!("--> Exiting Region A (Over-compressed)"); }
            return Some(Regime::A);
        }

        self.history_attractors.push_back(attractor);
        if is_jump {
            self.jumps_in_window += 1;
        }

        // Keep rolling window for attractors at 10000
        if self.history_attractors.len() > 10000 {
            let old = self.history_attractors.pop_front().unwrap();
            let old_next = self.history_attractors.front().unwrap();
            if old != *old_next {
                self.jumps_in_window -= 1;
            }

            // Check Region D: Limit cycle of 2 to 5 attractors over 10000 cycles
            if _cycle % 1000 == 0 {
                for period in 2..=5 {
                    let mut is_periodic = true;
                    let mut has_changes = false;
                    // Check if the sequence repeats exactly with `period`
                    let hist_slice: Vec<usize> = self.history_attractors.iter().copied().collect();
                    for i in 0..9000 {
                        if hist_slice[i] != hist_slice[i + period] {
                            is_periodic = false;
                            break;
                        }
                        if hist_slice[i] != hist_slice[i+1] {
                            has_changes = true;
                        }
                    }
                    if is_periodic && has_changes {
                        if self.debug { println!("--> Exiting Region D (Reverberating period {})", period); }
                        return Some(Regime::D);
                    }
                }

                // Check Region C: Overstimulated
                // If over 10000 cycles we have > 9000 jumps and it's not a limit cycle
                if self.jumps_in_window > 9000 {
                    if self.debug { println!("--> Exiting Region C (Overstimulated)"); }
                    return Some(Regime::C);
                }
            }
        }

        None
    }
}
