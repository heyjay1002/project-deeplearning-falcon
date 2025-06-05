import torch
print(torch.cuda.is_available())  # True 나오면 OK
print(torch.cuda.get_device_name(0))  # "RTX 3060" 등 출력(yolovenv2) PS C:\Users\Administrator> where python