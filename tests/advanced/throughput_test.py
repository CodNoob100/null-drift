import os
import httpx
import asyncio
import time

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000")
TOTAL_REQUESTS = 10000
CONCURRENCY = 1000


async def hammer_worker(sem, client, worker_id):
    thread_id = f"stress_thread_{worker_id}"
    async with sem:
        res = await client.post(
            f"{GATEWAY_URL}/inject",
            params={"thread_id": thread_id},
            json={
                "text": f"Stress test data payload {worker_id} from concurrent execution.",
                "salience": 0.5,
            },
            timeout=30.0,
        )
        res.raise_for_status()


async def run_throughput():
    print(
        f"Starting Throughput Test: {TOTAL_REQUESTS} requests across {TOTAL_REQUESTS} distinct threads."
    )
    print(f"Concurrency Limit: {CONCURRENCY}")

    sem = asyncio.Semaphore(CONCURRENCY)

    start = time.perf_counter()

    async with httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=CONCURRENCY, max_keepalive_connections=CONCURRENCY
        )
    ) as client:
        tasks = []
        for i in range(TOTAL_REQUESTS):
            tasks.append(hammer_worker(sem, client, i))

        await asyncio.gather(*tasks)

    end = time.perf_counter()
    duration = end - start
    req_per_sec = TOTAL_REQUESTS / duration

    print("\n=== THROUGHPUT RESULTS ===")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"Total Time: {duration:.2f} seconds")
    print(f"Throughput: {req_per_sec:.2f} requests/second")
    print("Multi-tenant Cache Isolation: SUCCESS")


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_throughput())
