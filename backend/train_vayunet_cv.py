import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
import pandas as pd
import os
import time

# Configurations for 4GB VRAM GPU
BATCH_SIZE = 16
EPOCHS = 3
LEARNING_RATE = 1e-4
CSV_FILE = "vayu_dataset.csv"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Using device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

class VayuNetDataset(Dataset):
    def __init__(self, csv_file, transform=None):
        self.data = pd.read_csv(csv_file)
        self.transform = transform

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        img_path = row['image_path']

        try:
            image = Image.open(img_path).convert("RGB")
        except Exception as e:
            # Fallback for missing/corrupt images
            image = Image.new("RGB", (224, 224))

        labels = torch.tensor([row['is_smoke'], row['is_dust'], row['is_fire'], row['has_plume']], dtype=torch.float32)

        if self.transform:
            image = self.transform(image)

        return image, labels

# Standard ImageNet transforms
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

print("Loading dataset...")
dataset = VayuNetDataset(CSV_FILE, transform=transform)
dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0) # num_workers=0 for Windows compatibility

print("Initializing EfficientNet-B0...")
model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)

# Replace classifier for 4 multi-label outputs
num_ftrs = model.classifier[1].in_features
model.classifier[1] = nn.Linear(num_ftrs, 4)
model = model.to(DEVICE)

# Multi-label loss function
criterion = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

# Automatic Mixed Precision for VRAM reduction
scaler = torch.amp.GradScaler('cuda')

print("Starting training loop...")
for epoch in range(EPOCHS):
    model.train()
    running_loss = 0.0
    start_time = time.time()

    for i, (inputs, labels) in enumerate(dataloader):
        inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)

        optimizer.zero_grad()

        # AMP context
        with torch.amp.autocast('cuda'):
            outputs = model(inputs)
            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        running_loss += loss.item()

        if (i+1) % 5 == 0 or (i+1) == len(dataloader):
            print(f"Epoch [{epoch+1}/{EPOCHS}], Step [{i+1}/{len(dataloader)}], Loss: {loss.item():.4f}")

    epoch_time = time.time() - start_time
    print(f"Epoch {epoch+1} completed in {epoch_time:.2f}s. Avg Loss: {running_loss/len(dataloader):.4f}")

print("Training complete. Saving model...")
torch.save(model.state_dict(), "vayunet_efficientnet_b0.pth")
print("Model saved to vayunet_efficientnet_b0.pth")
