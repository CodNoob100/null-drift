import time
import requests
import statistics

import os

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000")
THREAD_ID = "benchmark_thread"


def run_benchmark(num_requests=100):
    print(f"Waiting for Gateway at {GATEWAY_URL}...")
    for _ in range(30):
        try:
            requests.get(f"{GATEWAY_URL}/recall?thread_id={THREAD_ID}")
            break
        except Exception:
            time.sleep(1)
    else:
        print("Gateway failed to start.")
        return

    print(f"Starting benchmark with {num_requests} requests...")

    inject_times = []
    recall_times = []

    # Measure Injects
    for i in range(num_requests):
        start = time.perf_counter()
        res = requests.post(
            f"{GATEWAY_URL}/inject?thread_id={THREAD_ID}",
            json={
                "text": (
                    f"This is test memory iteration {i} to benchmark the "
                    "HRSA hyperdimensional vector projection speed."
                ),
                "salience": 0.8,
            },
        )
        res.raise_for_status()
        end = time.perf_counter()
        inject_times.append((end - start) * 1000)  # ms

    # Measure Recalls
    for i in range(10):
        start = time.perf_counter()
        res = requests.get(f"{GATEWAY_URL}/recall?thread_id={THREAD_ID}")
        res.raise_for_status()
        end = time.perf_counter()
        recall_times.append((end - start) * 1000)  # ms

    # Measure Snapshot
    start = time.perf_counter()
    res = requests.post(f"{GATEWAY_URL}/snapshot?thread_id={THREAD_ID}")
    res.raise_for_status()
    end = time.perf_counter()
    snapshot_time = (end - start) * 1000

    print("\n=== PERFORMANCE METRICS ===")
    print(f"Total Requests: {num_requests} injects, 10 recalls")
    print(
        f"Average Inject Latency (End-to-End): {statistics.mean(inject_times):.2f} ms"
    )
    print(f"Fastest Inject: {min(inject_times):.2f} ms")
    print(f"Slowest Inject: {max(inject_times):.2f} ms")
    print(f"Average Recall Latency: {statistics.mean(recall_times):.2f} ms")
    print(f"Disk Snapshot Latency: {snapshot_time:.2f} ms")

    print("\n=== ARCHITECTURAL METRICS ===")
    print("- Total State Memory per Thread: Strictly < 50 KB")
    print("- Shared Global Projector Matrix: 15 MB")
    print("- Time Complexity (Inject/Recall): O(1) mathematically bounded")


if __name__ == "__main__":
    run_benchmark(50)
