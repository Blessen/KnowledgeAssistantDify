import psutil
import time
from rich.console import Console
from rich.table import Table
from pynvml import (
    nvmlInit,
    nvmlDeviceGetCount,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetName,
    nvmlDeviceGetUtilizationRates,
)

console = Console()

# Initialize NVML for GPU tracking
nvmlInit()
gpu_count = nvmlDeviceGetCount()

# CPU tracking
cpu_samples = []
min_cpu = 100.0
max_cpu = 0.0

# Memory tracking
mem_samples = []
min_mem_used = float('inf')
max_mem_used = 0.0

# GPU tracking
gpu_util_samples = [{} for _ in range(gpu_count)]

while True:
    # --- CPU stats ---
    current_cpu = psutil.cpu_percent(interval=1)
    cpu_samples.append(current_cpu)
    min_cpu = min(min_cpu, current_cpu)
    max_cpu = max(max_cpu, current_cpu)
    avg_cpu = sum(cpu_samples) / len(cpu_samples)

    # --- Memory stats ---
    mem = psutil.virtual_memory()
    total_mem = round(mem.total / (1024**3), 2)
    used_mem = round((mem.total - mem.available) / (1024**3), 2)
    mem_percent = mem.percent

    mem_samples.append(used_mem)
    min_mem_used = min(min_mem_used, used_mem)
    max_mem_used = max(max_mem_used, used_mem)
    avg_mem_used = round(sum(mem_samples) / len(mem_samples), 2)

    # --- Swap stats ---
    swap = psutil.swap_memory()
    total_swap = round(swap.total / (1024**3), 2)
    used_swap = round(swap.used / (1024**3), 2)
    swap_percent = swap.percent

    # --- Network stats ---
    net = psutil.net_io_counters()

    # --- GPU stats ---
    gpu_rows = []
    for i in range(gpu_count):
        handle = nvmlDeviceGetHandleByIndex(i)
        name = nvmlDeviceGetName(handle)
        name = name.decode("utf-8") if isinstance(name, bytes) else name
        utilization = nvmlDeviceGetUtilizationRates(handle)
        gpu_util = utilization.gpu  # in percent

        # Initialize stats tracking for GPU i
        if "samples" not in gpu_util_samples[i]:
            gpu_util_samples[i] = {
                "name": name,
                "samples": [],
                "min": 100.0,
                "max": 0.0
            }

        gpu_util_samples[i]["samples"].append(gpu_util)
        gpu_util_samples[i]["min"] = min(gpu_util_samples[i]["min"], gpu_util)
        gpu_util_samples[i]["max"] = max(gpu_util_samples[i]["max"], gpu_util)
        avg = sum(gpu_util_samples[i]["samples"]) / len(gpu_util_samples[i]["samples"])

        gpu_rows.append((name, gpu_util, gpu_util_samples[i]["min"], gpu_util_samples[i]["max"], avg))

    # Display Table
    table = Table(title="System Monitor (Live)")

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Current CPU Usage", f"{current_cpu:.2f}%")
    # table.add_row("Min CPU Usage", f"{min_cpu:.2f}%")
    table.add_row("Max CPU Usage", f"{max_cpu:.2f}%")
    table.add_row("Avg CPU Usage", f"{avg_cpu:.2f}%")

    table.add_row("Memory Usage (%)", f"{mem_percent}%")
    table.add_row("Memory Used (Current)", f"{used_mem} GB / {total_mem} GB")
    # table.add_row("Memory Used (Min)", f"{min_mem_used:.2f} GB")
    table.add_row("Memory Used (Max)", f"{max_mem_used:.2f} GB")
    table.add_row("Memory Used (Avg)", f"{avg_mem_used:.2f} GB")

    table.add_row("Swap Usage (%)", f"{swap_percent}%")
    table.add_row("Swap Used", f"{used_swap} GB / {total_swap} GB")

    # Define these before your while loop
    prev_net = psutil.net_io_counters()
    prev_time = time.time()

    # Inside your while loop (after 1 second sleep)
    curr_net = psutil.net_io_counters()
    curr_time = time.time()

    elapsed_time = curr_time - prev_time
    sent_speed = (curr_net.bytes_sent - prev_net.bytes_sent) / elapsed_time / 1e6  # MB/s
    recv_speed = (curr_net.bytes_recv - prev_net.bytes_recv) / elapsed_time / 1e6  # MB/s

    table.add_row("Net Upload Speed", f"{sent_speed:.2f} MB/s")
    table.add_row("Net Download Speed", f"{recv_speed:.2f} MB/s")

    # Update previous values
    prev_net = curr_net
    prev_time = curr_time

    for name, current, min_g, max_g, avg_g in gpu_rows:
        table.add_row(f"{name} - Current GPU", f"{current:.2f}%")
        # table.add_row(f"{name} - Min GPU", f"{min_g:.2f}%")
        table.add_row(f"{name} - Max GPU", f"{max_g:.2f}%")
        table.add_row(f"{name} - Avg GPU", f"{avg_g:.2f}%")

    console.clear()
    console.print(table)