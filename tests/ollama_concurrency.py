import asyncio
import httpx
import psutil
import subprocess
import time
from statistics import mean
from rich.console import Console

# === CONFIG ===
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5vl:32b"  # update as needed
CONCURRENT_USERS = 1

# === MONITORING DATA ===
cpu_samples, mem_samples = [], []
gpu_utilization = {}
gpu_mem_utilization = {}
net_sent, net_recv = [], []
api_response_times = []

console = Console()

def get_gpu_util():
    try:
        output = subprocess.check_output([
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits"
        ])
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

async def hit_ollama(user_id: int):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": "Write a Hello World in Python."}
        ]
    }

    async with httpx.AsyncClient(timeout=120) as client:
        start = time.time()
        try:
            res = await client.post(OLLAMA_URL, json=payload)
            duration = round(time.time() - start, 2)
            api_response_times.append((user_id, duration, res.status_code))
            return res.status_code
        except Exception as e:
            duration = round(time.time() - start, 2)
            api_response_times.append((user_id, duration, f"Failed: {str(e)}"))
            return None

async def load_test():
    tasks = [hit_ollama(i) for i in range(CONCURRENT_USERS)]
    return await asyncio.gather(*tasks)

async def monitor():
    prev_net = psutil.net_io_counters()
    prev_time = time.time()

    while True:
        cpu_samples.append(psutil.cpu_percent(interval=1))
        mem_samples.append(psutil.virtual_memory().percent)

        for name, usage, mem_percent in get_gpu_util():
            gpu_utilization.setdefault(name, []).append(usage)
            gpu_mem_utilization.setdefault(name, []).append(mem_percent)

        curr_net = psutil.net_io_counters()
        curr_time = time.time()
        elapsed = curr_time - prev_time

        if elapsed > 0:
            upload = (curr_net.bytes_sent - prev_net.bytes_sent) / elapsed / 1e6
            download = (curr_net.bytes_recv - prev_net.bytes_recv) / elapsed / 1e6
            net_sent.append(upload)
            net_recv.append(download)

        prev_net = curr_net
        prev_time = curr_time

        await asyncio.sleep(0)

def stat_line(label, values):
    if values:
        return f"{label}: Min={min(values):.2f}, Max={max(values):.2f}, Avg={mean(values):.2f}"
    return f"{label}: No Data"

async def main():
    console.rule(f"[bold cyan]Running Ollama Concurrency Test with {CONCURRENT_USERS} users...")
    start = time.time()
    monitor_task = asyncio.create_task(monitor())
    await load_test()
    end = time.time()
    monitor_task.cancel()

    total_duration = round(end - start, 2)
    console.rule("[bold green] Test Completed")

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