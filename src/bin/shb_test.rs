use null_drift::encoder::SemanticEncoder;
use null_drift::spl::Projector;
use null_drift::amn::AttractorIndex;
use ndarray::Array1;
use rand::Rng;

fn main() {
    println!("=== Phase 1: Semantic-Hyperdimensional Bridge (SHB) Testbench ===");
    
    // 1. Initialize Components
    let projector = Projector::new(384, 10000);
    let mut amn = AttractorIndex::new(3000); // Allow up to 30% bit flips (3000 out of 10000)

    // Simulate dense embeddings from SemanticEncoder (e.g. 384-dimensional from MiniLM)
    println!("Generating mock 384D dense semantic embeddings...");
    let mut rng = rand::thread_rng();
    let dense_embeddings: Vec<Array1<f32>> = (0..3).map(|_| {
        Array1::from_shape_fn(384, |_| rng.gen_range(-1.0..1.0))
    }).collect();

    let texts = vec![
        "User is an admin",
        "Target system is Ubuntu",
        "Port 22 is open"
    ];

    // 2. Project
    println!("Projecting dense embeddings into 10,000D Bipolar Space...");
    let mut hypervectors = Vec::new();
    for (i, emb) in dense_embeddings.iter().enumerate() {
        let hv = projector.project_to_hypervector(emb.clone());
        println!("  - Embedded Vector {} (popcount: {})", i, hv.iter().filter(|&&b| b > 0.0).count());
        
        // Store clean hypervector in AMN
        amn.store(hv.clone(), texts[i].to_string());
        hypervectors.push(hv);
        println!("Encoded and stored: '{}'", texts[i]);
    }

    // 3. Bind using element-wise multiplication (Mock circular convolution for bipolar)
    // S = A ∘ B ∘ C
    let mut bound_state = Array1::<f32>::ones(10000);
    for hv in &hypervectors {
        bound_state = bound_state * hv;
    }
    
    // Unroll (unbind) "Target system is Ubuntu" to retrieve it.
    // In bipolar representation, A ∘ A = 1. So unbinding B from S is just S ∘ A ∘ C.
    let mut unrolled = bound_state.clone();
    unrolled = unrolled * &hypervectors[0]; // unbind A
    unrolled = unrolled * &hypervectors[2]; // unbind C

    // 4. Add 20% noise to the unrolled vector
    let mut rng = rand::thread_rng();
    let mut noise_count = 0;
    for val in unrolled.iter_mut() {
        if rng.gen_range(0.0..1.0) < 0.20 {
            *val *= -1.0;
            noise_count += 1;
        }
    }
    println!("Added {} bit flips (20% noise) to unrolled vector.", noise_count);

    // 5. AMN Cleanup
    match amn.cleanup(&unrolled) {
        Some(recovered) => {
            println!("AMN Recovery SUCCESS! Recovered string: '{}'", recovered);
            assert_eq!(recovered, "Target system is Ubuntu");
        },
        None => {
            println!("AMN Recovery FAILED! No match found within threshold.");
            std::process::exit(1);
        }
    }
}
