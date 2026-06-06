use dotenvy::dotenv;
use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub sweep_sigma_min: f32,
    pub sweep_sigma_max: f32,
    pub sweep_sigma_step: f32,
    pub sweep_f_cons_steps: Vec<usize>,
    pub sweep_eta_min: f32,
    pub sweep_eta_max: f32,
    pub sweep_eta_step: f32,
    pub debug_memory_logs: bool,
}

impl Config {
    pub fn load() -> Self {
        dotenv().ok();

        let f_cons_str = env::var("SWEEP_F_CONS_STEPS")
            .unwrap_or_else(|_| "10,25,50,100,250,500,1000".to_string());
        
        let sweep_f_cons_steps: Vec<usize> = f_cons_str
            .split(',')
            .map(|s| s.trim().parse().expect("Invalid SWEEP_F_CONS_STEPS"))
            .collect();

        Self {
            sweep_sigma_min: get_env_f32("SWEEP_SIGMA_MIN", 0.1),
            sweep_sigma_max: get_env_f32("SWEEP_SIGMA_MAX", 5.0),
            sweep_sigma_step: get_env_f32("SWEEP_SIGMA_STEP", 0.2),
            sweep_f_cons_steps,
            sweep_eta_min: get_env_f32("SWEEP_ETA_MIN", 0.70),
            sweep_eta_max: get_env_f32("SWEEP_ETA_MAX", 0.99),
            sweep_eta_step: get_env_f32("SWEEP_ETA_STEP", 0.05),
            debug_memory_logs: env::var("DEBUG_MEMORY_LOGS").unwrap_or_else(|_| "0".to_string()) == "1",
        }
    }
}

fn get_env_f32(key: &str, default: f32) -> f32 {
    env::var(key)
        .unwrap_or_else(|_| default.to_string())
        .parse()
        .unwrap_or_else(|_| panic!("Invalid {}", key))
}
