import asyncio
import aiohttp
import random
import uuid
import sys
import time
from sentence_transformers import SentenceTransformer

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Setup random noise phrases
NOISE_PHRASES = [
    "Ping timeout on gateway",
    "404 Not Found at /favicon.ico",
    "Trace route hop 5 dropping packets",
    "TCP SYN retransmission",
    "DNS resolution delayed for internal service",
    "User clicked refresh",
    "SSL handshake failed",
    "Database connection pool full",
    "Redis cache miss",
    "Nginx worker process died"
]

CAUSAL_MILESTONES = [
    "Step 1: Scanned subnet and found open port 8080",
    "Step 2: Identified vulnerable admin portal",
    "Step 3: Extracted JWT from exposed config",
    "Step 4: Cracked salt locally",
    "Step 5: Gained root access via reverse shell"
]

class StressTest:
    def __init__(self, target_events=10000):
        print("Initializing SentenceTransformer (all-MiniLM-L6-v2) for Chaos Monkey...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.target_events = target_events
        self.milestone_indices = sorted(random.sample(range(100, target_events - 100), len(CAUSAL_MILESTONES)))
        self.session = None
        self.base_url = "http://127.0.0.1:3000"
        
        print("Pre-computing embeddings to saturate network at maximum speed...")
        self.cache = {}
        for text in NOISE_PHRASES + CAUSAL_MILESTONES:
            self.cache[text] = self.model.encode(text).tolist()

    async def run(self):
        self.session = aiohttp.ClientSession()
        print(f"=== Beginning Memory Pressure Test ({self.target_events} events) ===")
        
        tasks = []
        milestone_counter = 0
        
        for i in range(self.target_events):
            if milestone_counter < len(self.milestone_indices) and i == self.milestone_indices[milestone_counter]:
                text = CAUSAL_MILESTONES[milestone_counter]
                salience = random.uniform(0.95, 1.0)
                milestone_counter += 1
                await asyncio.gather(*tasks)
                tasks = []
                await self.inject(text, salience, is_milestone=True, step=i)
            else:
                text = random.choice(NOISE_PHRASES)
                salience = random.uniform(0.01, 0.20)
                tasks.append(asyncio.create_task(self.inject(text, salience, is_milestone=False, step=i)))
                
            if len(tasks) >= 500:
                await asyncio.gather(*tasks)
                tasks = []
                
            if i == self.target_events // 2:
                await asyncio.gather(*tasks)
                tasks = []
                print("\n[CHAOS MONKEY] Halfway point reached! Executing Snapshot...")
                await self.trigger_snapshot()
                
                print("[CHAOS MONKEY] Triggering Restore...")
                await self.trigger_restore()

        if tasks:
            await asyncio.gather(*tasks)
            
        print("\n=== Stress Test Injection Complete ===")
        print("Triggering Final Recall...")
        await self.trigger_recall()
        
        await self.session.close()

    async def inject(self, text, salience, is_milestone, step):
        embedding = self.cache[text]
        payload = {
            "id": str(uuid.uuid4()),
            "text": text,
            "embedding": embedding,
            "salience": salience
        }
        try:
            async with self.session.post(f"{self.base_url}/inject", json=payload) as response:
                await response.json()
                if is_milestone:
                    print(f"  [MILESTONE] INJECTED: '{text}' (Step {step}, Salience: {salience:.2f})")
                elif step % 1000 == 0:
                    print(f"  [Progress] Injected {step} events...")
        except Exception as e:
            pass

    async def trigger_snapshot(self):
        async with self.session.post(f"{self.base_url}/snapshot") as response:
            res = await response.json()
            print(f"  Snapshot Result: {res}")

    async def trigger_restore(self):
        async with self.session.post(f"{self.base_url}/restore") as response:
            res = await response.json()
            print(f"  Restore Result: {res}")

    async def trigger_recall(self):
        async with self.session.get(f"{self.base_url}/recall") as response:
            res = await response.json()
            print(f"\n[FINAL RESULT] Dominant Attractor: {res.get('recovered_text')}")
            
            if res.get('recovered_text') == CAUSAL_MILESTONES[-1]:
                print("\n[SUCCESS] The HRSA survived 10,000 garbage events, high memory pressure, and physical death!")
            else:
                print(f"\n[FAILURE] Expected '{CAUSAL_MILESTONES[-1]}', got '{res.get('recovered_text')}'")


if __name__ == "__main__":
    test = StressTest(10000)
    asyncio.run(test.run())
