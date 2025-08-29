from pynvml import (
    nvmlInit,
    nvmlDeviceGetCount,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetName,
    nvmlDeviceGetUtilizationRates,
    nvmlShutdown
)

nvmlInit()

gpu_count = nvmlDeviceGetCount()

for i in range(gpu_count):
    handle = nvmlDeviceGetHandleByIndex(i)
    name = nvmlDeviceGetName(handle)
    utilization = nvmlDeviceGetUtilizationRates(handle)

    print(f"{name} - GPU Utilization: {utilization.gpu}%, Memory Utilization: {utilization.memory}%")

nvmlShutdown()