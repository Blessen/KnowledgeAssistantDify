import asyncio
import psutil
import subprocess
import time
from statistics import mean
from rich.console import Console

# === CONFIG ===
DURATION_SECONDS = 60  # how long to monitor idle stats

# === MONITORING DATA ===
cpu_samples, mem_samples = [], []
gpu_utilization = {}         # {gpu_name: [util%]}
gpu_mem_utilization = {}     # {gpu_name: [mem%]}

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

async def monitor_idle(duration: int):
    start = time.time()
    while (time.time() - start) < duration:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()

        cpu_samples.append(cpu)
        mem_samples.append(mem.percent)

        for name, usage, mem_percent in get_gpu_util():
            gpu_utilization.setdefault(name, []).append(usage)
            gpu_mem_utilization.setdefault(name, []).append(mem_percent)

        await asyncio.sleep(0)

def stat_line(label, values):
    if values:
        return f"{label}: Min={min(values):.2f}, Max={max(values):.2f}, Avg={mean(values):.2f}"
    return f"{label}: No Data"

async def main():
    console.rule(f"[bold cyan]Monitoring Idle System Performance for {DURATION_SECONDS} seconds...")
    await monitor_idle(DURATION_SECONDS)
    console.rule("[bold green] Idle Performance Summary")

    console.print(stat_line("CPU (%)", cpu_samples))
    console.print(stat_line("Memory (%)", mem_samples))

    if gpu_utilization:
        for name, samples in gpu_utilization.items():
            console.print(stat_line(f"{name} GPU (%)", samples))
    else:
        console.print("GPU Utilization: No Data")

    if gpu_mem_utilization:
        for name, samples in gpu_mem_utilization.items():
            console.print(stat_line(f"{name} GPU Memory (%)", samples))
    else:
        console.print("GPU Memory: No Data")

if __name__ == "__main__":
    asyncio.run(main())