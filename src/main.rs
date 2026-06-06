mod config;
mod hrsa;
mod telemetry;

use config::Config;
use hrsa::HrsaSimulator;
use telemetry::Regime;
use std::fs::File;
use std::time::Instant;
use rayon::prelude::*;
use serde::Serialize;

#[derive(Serialize)]
struct SweepResult {
    sigma_w_sq: f32,
    f_cons: usize,
    eta_cleanup: f32,
    regime: String,
    time_to_transition: usize,
}

fn main() {
    let config = Config::load();
    println!("Loaded config:");
    println!("  sigma: {:.2} to {:.2} (step {:.2})", config.sweep_sigma_min, config.sweep_sigma_max, config.sweep_sigma_step);
    println!("  f_cons steps: {:?}", config.sweep_f_cons_steps);
    println!("  eta: {:.2} to {:.2} (step {:.2})", config.sweep_eta_min, config.sweep_eta_max, config.sweep_eta_step);
    println!("Starting phase space sweep...");
    
    let mut params = Vec::new();

    let mut sigma = config.sweep_sigma_min;
    // Add small epsilon to float max comparisons to prevent missing last step due to floating point inaccuracies
    while sigma <= config.sweep_sigma_max + 1e-4 {
        for &f_cons in &config.sweep_f_cons_steps {
            let mut eta = config.sweep_eta_min;
            while eta <= config.sweep_eta_max + 1e-4 {
                params.push((sigma, f_cons, eta));
                eta += config.sweep_eta_step;
            }
        }
        sigma += config.sweep_sigma_step;
    }

    println!("Total combinations to simulate: {}", params.len());

    let start_time = Instant::now();

    let results: Vec<SweepResult> = params.into_par_iter().map(|(sigma_w_sq, f_cons, eta_cleanup)| {
        let mut sim = HrsaSimulator::new(sigma_w_sq, f_cons, eta_cleanup, config.debug_memory_logs);
        let (regime, cycles) = sim.run();

        let regime_str = match regime {
            Regime::A => "A",
            Regime::B => "B",
            Regime::C => "C",
            Regime::D => "D",
            Regime::E => "E",
        };

        SweepResult {
            sigma_w_sq,
            f_cons,
            eta_cleanup,
            regime: regime_str.to_string(),
            time_to_transition: cycles,
        }
    }).collect();

    println!("Sweep completed in {:?}", start_time.elapsed());

    let mut wtr = csv::Writer::from_writer(File::create("phase_space_results.csv").unwrap());
    for res in results {
        wtr.serialize(res).unwrap();
    }
    wtr.flush().unwrap();
    
    println!("Results saved to phase_space_results.csv");
}
