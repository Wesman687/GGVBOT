import torch
torch.tensor([1.0]).cuda() 

print("🔥 PyTorch CUDA Test 🔥")
print("CUDA Available:", torch.cuda.is_available())
print("Device Count:", torch.cuda.device_count())

if torch.cuda.is_available():
    print("Active GPU:", torch.cuda.get_device_name(0))
    print("Memory Allocated:", torch.cuda.memory_allocated(0))
    print("Memory Reserved:", torch.cuda.memory_reserved(0))
else:
    print("❌ CUDA is not available. Using CPU.")