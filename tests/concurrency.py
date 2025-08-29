import asyncio
import httpx
import psutil
import subprocess
import time
from rich.console import Console
from statistics import mean

# === CONFIG ===
# API_URL = "https://5d72d2d8b484.ngrok-free.app/v1/chat-messages"
API_URL = "http://localhost:5001/v1/chat-messages"
API_KEY = "Bearer app-kSfCgDikiqeXXWAsTi9tq2z3"
APP_ID = "24efb910-d0b3-4a84-bf2d-70a7ba56f570"
CONCURRENT_USERS = 12

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": API_KEY,
}

PAYLOAD = {
    "app_id": APP_ID,
    "query": "What is Optiprime?",
    "inputs": {},
    "mode": "blocking"
}

# === MONITORING DATA ===
cpu_samples, mem_samples = [], []
net_sent, net_recv = [], []
gpu_utilization = {}
gpu_mem_utilization = {}
api_response_times = []

console = Console()

def get_gpu_util():
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ]
        )
        lines = output.decode().strip().splitlines()
        results = []
        for line in lines:
            name, usage, mem_used, mem_total = map(str.strip, line.split(",", 3))
            usage = int(usage)
            mem_percent = round((int(mem_used) / int(mem_total)) * 100, 2)
            results.append((name, usage, mem_percent))
        return results
    except Exception:
        return []

async def hit_api(user_id: int):
    payload = PAYLOAD.copy()
    payload["user"] = f"k6-test-user-{user_id}"

    async with httpx.AsyncClient(timeout=None) as client:
        start = time.time()
        try:
            res = await client.post(API_URL, headers=HEADERS, json=payload)
            duration = round(time.time() - start, 2)
            api_response_times.append((user_id, duration, res.status_code))
            return res.status_code
        except Exception as e:
            duration = round(time.time() - start, 2)
            api_response_times.append((user_id, duration, f"Failed: {str(e)}"))
            return None

async def load_test():
    tasks = [hit_api(i) for i in range(CONCURRENT_USERS)]
    return await asyncio.gather(*tasks)

async def monitor():
    prev_net = psutil.net_io_counters()
    prev_time = time.time()

    while True:
        current_cpu = psutil.cpu_percent(interval=1)
        cpu_samples.append(current_cpu)

        mem = psutil.virtual_memory()
        mem_samples.append(mem.percent)

        for name, usage, mem_percent in get_gpu_util():
            gpu_utilization.setdefault(name, []).append(usage)
            gpu_mem_utilization.setdefault(name, []).append(mem_percent)

        curr_net = psutil.net_io_counters()
        curr_time = time.time()
        elapsed = curr_time - prev_time

        if elapsed > 0:
            net_sent.append((curr_net.bytes_sent - prev_net.bytes_sent) / elapsed / 1e6)
            net_recv.append((curr_net.bytes_recv - prev_net.bytes_recv) / elapsed / 1e6)

        prev_net = curr_net
        prev_time = curr_time

        await asyncio.sleep(0)

async def main():
    start = time.time()
    monitor_task = asyncio.create_task(monitor())
    await load_test()
    end = time.time()

    monitor_task.cancel()
    total_duration = round(end - start, 2)

    console.rule("[bold green] Test Completed")

    def stat_line(label, values):
        if values:
            return f"{label}: Min={min(values):.2f}, Max={max(values):.2f}, Avg={mean(values):.2f}"
        return f"{label}: No Data"

    console.print(stat_line("CPU (%)", cpu_samples))
    console.print(stat_line("Memory (%)", mem_samples))
    console.print(stat_line("Net Upload (MB/s)", net_sent))
    console.print(stat_line("Net Download (MB/s)", net_recv))

    if gpu_utilization:
        for name, samples in gpu_utilization.items():
            console.print(stat_line(f"{name} GPU (%)", samples))
    else:
        console.print("GPU: No Data")

    if gpu_mem_utilization:
        for name, samples in gpu_mem_utilization.items():
            console.print(stat_line(f"{name} GPU Memory (%)", samples))
    else:
        console.print("GPU: No Data")

    console.print("\n[bold yellow]Individual API Response Times:")
    for uid, t, status in api_response_times:
        mins, secs = divmod(t, 60)
        console.print(f"User {uid}: Time = {int(mins)}m {secs:.2f}s, Status = {status}")

    mins, secs = divmod(total_duration, 60)
    console.print(f"\n[bold cyan]Total Test Duration: {int(mins)}m {secs:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())