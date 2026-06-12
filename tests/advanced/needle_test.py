import os
import httpx
import uuid
import random
import string
import asyncio
import time

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000")
THREAD_ID = f"needle_thread_{uuid.uuid4().hex[:8]}"

NEEDLE = "The nuclear launch code is 8402-DELTA-X"


def generate_noise():
    return "".join(random.choices(string.ascii_letters + string.digits, k=50))


async def inject_event(client, thread_id, text, salience):
    res = await client.post(
        f"{GATEWAY_URL}/inject",
        params={"thread_id": thread_id},
        json={"text": text, "salience": salience},
        timeout=10.0,
    )
    res.raise_for_status()


async def run_test():
    print(f"Starting Needle-in-a-Haystack test on thread: {THREAD_ID}")

    # We use a relatively high connection limit since the rust gateway is extremely fast
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=200)) as client:
        # 1. Inject the needle
        print(f"Injecting Needle: '{NEEDLE}' (Salience 1.0)")
        await inject_event(client, THREAD_ID, NEEDLE, 1.0)

        # 2. Inject 10,000 noise events
        print("Injecting 10,000 noise events (Salience 0.1)...")
        start = time.perf_counter()

        total = 10000
        batch_size = 500

        for i in range(0, total, batch_size):
            tasks = []
            for _ in range(batch_size):
                tasks.append(inject_event(client, THREAD_ID, generate_noise(), 0.1))
            await asyncio.gather(*tasks)
            print(f"Injected {i + batch_size}/{total} noise events...")

        end = time.perf_counter()
        print(f"Finished 10,000 noise injections in {end - start:.2f} seconds.")

        # 3. Recall
        print("Recalling dominant state...")
        res = await client.get(
            f"{GATEWAY_URL}/recall", params={"thread_id": THREAD_ID}, timeout=60.0
        )
        res.raise_for_status()
        data = res.json()

        recovered = data.get("recovered_text")
        print(f"Recovered Text: {recovered}")

        if recovered == NEEDLE:
            print(
                "\n[SUCCESS] Needle perfectly recovered after 10,000 noise permutations!"
            )
            print(
                "The Attractor Memory Network (AMN) successfully preserved the high-salience anchor."
            )
        else:
            print("\n[FAILURE] Needle was lost or blurred in the thermodynamic drift!")


if __name__ == "__main__":
    asyncio.run(run_test())
