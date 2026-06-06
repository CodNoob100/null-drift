from gateway import CognitiveGateway
import time

def run_causal_chain_test():
    print("=== Null-Drift Phase 2: Causal Chain Test ===")
    gateway = CognitiveGateway()
    
    # Simulate a sequential workflow (e.g., cyber-reconnaissance task)
    
    # 1. Low salience noise
    gateway.commit_memory("Scanning subnet 192.168.1.0/24", salience=0.2)
    time.sleep(0.5)
    
    # 2. Medium salience discovery
    gateway.commit_memory("Found open port 8080 on .15", salience=0.5)
    time.sleep(0.5)
    
    # 3. High salience critical milestone (The target memory)
    gateway.commit_memory("Discovered unauthenticated admin API endpoint", salience=1.0)
    time.sleep(0.5)
    
    # 4. Low salience noise (post-milestone drift)
    gateway.commit_memory("Pinging external DNS", salience=0.1)
    time.sleep(0.5)
    
    # Final recall to verify salience crushing
    print("\n--- Testing Retrieval ---")
    dominant_memory = gateway.recall_state()
    
    expected = "Discovered unauthenticated admin API endpoint"
    if dominant_memory == expected:
        print("\n[SUCCESS] The HRSA physics successfully preserved the causal milestone!")
    else:
        print(f"\n[FAILURE] Expected '{expected}', but got '{dominant_memory}'.")

if __name__ == "__main__":
    run_causal_chain_test()
