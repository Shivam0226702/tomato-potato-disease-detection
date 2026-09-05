#!/usr/bin/env python3
"""
train.py — Train EfficientNet-B0 for Tomato & Potato disease classification.

Usage
-----
    python train.py                          # full training (default 30 epochs)
    python train.py --epochs 50              # custom epochs
    python train.py --smoke-test             # 1-epoch smoke test
    python train.py --batch-size 16 --lr 5e-4
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
from sklearn.model_selection import train_test_split
from tqdm import tqdm


# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_ROOT = PROJECT_ROOT / "Dataset"
RESULTS_DIR  = PROJECT_ROOT / "results"

CLASS_NAMES = sorted([
    "Potato___Early_blight",
    "Potato___Healthy",
    "Potato___Late_blight",
    "Tomato___Early_blight",
    "Tomato___Healthy",
    "Tomato___Late_blight",
])

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
IMAGENET_MEAN    = [0.485, 0.456, 0.406]
IMAGENET_STD     = [0.229, 0.224, 0.225]
IMAGE_SIZE       = 224   # EfficientNet-B0 native input size


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="Train EfficientNet-B0 for plant disease classification"
    )
    p.add_argument("--epochs",       type=int,   default=30,   help="Training epochs (default: 30)")
    p.add_argument("--batch-size",   type=int,   default=32,   help="Batch size (default: 32)")
    p.add_argument("--lr",           type=float, default=1e-3, help="Initial learning rate (default: 1e-3)")
    p.add_argument("--weight-decay", type=float, default=1e-4, help="AdamW weight decay (default: 1e-4)")
    p.add_argument("--patience",     type=int,   default=7,    help="Early-stopping patience (default: 7)")
    p.add_argument("--seed",         type=int,   default=42,   help="Random seed (default: 42)")
    p.add_argument("--smoke-test",   action="store_true",      help="Run a 1-epoch smoke test")
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════════════
#  REPRODUCIBILITY
# ═══════════════════════════════════════════════════════════════════════

def set_seed(seed: int):
    """Pin every source of randomness for reproducible results."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark     = False


# ═══════════════════════════════════════════════════════════════════════
#  DATASET  (two-level walk reused from verify_dataset.py)
# ═══════════════════════════════════════════════════════════════════════

def collect_image_paths(dataset_root: Path, class_names: list[str]):
    """
    Walk  Dataset / <crop> / <class_name> / *.jpg  and return parallel
    lists of absolute paths and integer labels.

    The two-level traversal mirrors the pattern used in the earlier
    verification script.
    """
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}
    image_paths: list[str] = []
    labels: list[int]      = []

    for crop_dir in sorted(dataset_root.iterdir()):
        if not crop_dir.is_dir():
            continue
        for class_dir in sorted(crop_dir.iterdir()):
            if not class_dir.is_dir():
                continue
            class_name = class_dir.name
            if class_name not in class_to_idx:
                print(f"  [WARNING] Skipping unknown class folder: {class_name}")
                continue
            label = class_to_idx[class_name]
            for img_file in sorted(class_dir.iterdir()):
                if img_file.is_file() and img_file.suffix.lower() in IMAGE_EXTENSIONS:
                    image_paths.append(str(img_file))
                    labels.append(label)

    return image_paths, labels


class PlantDiseaseDataset(Dataset):
    """Simple map-style dataset with configurable transforms."""

    def __init__(self, image_paths: list[str], labels: list[int], transform=None):
        self.image_paths = image_paths
        self.labels      = labels
        self.transform   = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image = Image.open(self.image_paths[idx]).convert("RGB")
        label = self.labels[idx]
        if self.transform:
            image = self.transform(image)
        return image, label


# ═══════════════════════════════════════════════════════════════════════
#  TRANSFORMS
# ═══════════════════════════════════════════════════════════════════════

def get_transforms():
    """Return (train_transform, val_test_transform)."""
    train_tf = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.3),
        transforms.RandomRotation(degrees=20),
        transforms.ColorJitter(brightness=0.2, contrast=0.2,
                               saturation=0.2, hue=0.1),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

    val_tf = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

    return train_tf, val_tf


# ═══════════════════════════════════════════════════════════════════════
#  STRATIFIED SPLIT  (70 / 15 / 15 — no data leakage)
# ═══════════════════════════════════════════════════════════════════════

def create_splits(image_paths, labels, seed=42):
    """Return (train, val, test) as (paths, labels) tuples."""
    # 70 % train  ↔  30 % temp
    train_p, temp_p, train_l, temp_l = train_test_split(
        image_paths, labels,
        test_size=0.30, random_state=seed, stratify=labels,
    )
    # 50/50 on the 30 % temp  →  15 % val + 15 % test
    val_p, test_p, val_l, test_l = train_test_split(
        temp_p, temp_l,
        test_size=0.50, random_state=seed, stratify=temp_l,
    )
    return (train_p, train_l), (val_p, val_l), (test_p, test_l)


# ═══════════════════════════════════════════════════════════════════════
#  MODEL
# ═══════════════════════════════════════════════════════════════════════

def create_model(num_classes: int):
    """EfficientNet-B0 with ImageNet weights and a fresh classifier head."""
    model = models.efficientnet_b0(
        weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1
    )
    in_features = model.classifier[1].in_features   # 1280
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


# ═══════════════════════════════════════════════════════════════════════
#  EARLY STOPPING
# ═══════════════════════════════════════════════════════════════════════

class EarlyStopping:
    """Stop training when val loss stops improving for *patience* epochs."""

    def __init__(self, patience: int = 7, min_delta: float = 0.0):
        self.patience   = patience
        self.min_delta  = min_delta
        self.counter    = 0
        self.best_loss  = None
        self.should_stop = False

    def __call__(self, val_loss: float):
        if self.best_loss is None or val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter   = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True


# ═══════════════════════════════════════════════════════════════════════
#  TRAIN / VALIDATE HELPERS
# ═══════════════════════════════════════════════════════════════════════

def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = total = 0

    pbar = tqdm(loader, desc="  Train", leave=False, file=sys.stdout)
    for images, labels in pbar:
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, preds = outputs.max(1)
        total   += labels.size(0)
        correct += preds.eq(labels).sum().item()

        pbar.set_postfix(loss=f"{loss.item():.4f}",
                         acc=f"{100.0 * correct / total:.1f}%")

    return running_loss / total, correct / total


@torch.no_grad()
def validate(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = total = 0

    pbar = tqdm(loader, desc="  Val  ", leave=False, file=sys.stdout)
    for images, labels in pbar:
        images, labels = images.to(device), labels.to(device)

        outputs = model(images)
        loss    = criterion(outputs, labels)

        running_loss += loss.item() * images.size(0)
        _, preds = outputs.max(1)
        total   += labels.size(0)
        correct += preds.eq(labels).sum().item()

    return running_loss / total, correct / total


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    args = parse_args()

    if args.smoke_test:
        args.epochs = 1
        print("=" * 60)
        print("  SMOKE TEST MODE  —  running 1 epoch only")
        print("=" * 60)

    set_seed(args.seed)

    # ── Device ────────────────────────────────────────────────
    if torch.cuda.is_available():
        device   = torch.device("cuda")
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem  = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"\n[Device]  CUDA  —  {gpu_name}  ({gpu_mem:.1f} GB)")
    else:
        device   = torch.device("cpu")
        gpu_name = None
        print("\n[Device]  CPU  (no CUDA GPU detected)")

    # ── Collect images ────────────────────────────────────────
    print(f"\n[Dataset] Scanning: {DATASET_ROOT}")
    image_paths, labels = collect_image_paths(DATASET_ROOT, CLASS_NAMES)
    print(f"          Found {len(image_paths)} images across {len(CLASS_NAMES)} classes")

    class_counts = Counter(labels)
    for idx, name in enumerate(CLASS_NAMES):
        print(f"          [{idx}] {name}: {class_counts[idx]}")

    # ── Stratified split ──────────────────────────────────────
    (train_p, train_l), (val_p, val_l), (test_p, test_l) = \
        create_splits(image_paths, labels, seed=args.seed)

    print(f"\n[Split]   70 / 15 / 15  (stratified, seed={args.seed})")
    print(f"          Train:      {len(train_p):>5}")
    print(f"          Validation: {len(val_p):>5}")
    print(f"          Test:       {len(test_p):>5}")

    # ── Transforms & loaders ──────────────────────────────────
    train_tf, val_tf = get_transforms()

    train_ds = PlantDiseaseDataset(train_p, train_l, transform=train_tf)
    val_ds   = PlantDiseaseDataset(val_p,   val_l,   transform=val_tf)
    # test_ds is created but not used during training — reserved for evaluate.py
    test_ds  = PlantDiseaseDataset(test_p,  test_l,  transform=val_tf)

    # Windows cannot safely use num_workers > 0 without extra boilerplate
    num_workers = 0 if sys.platform == "win32" else min(4, os.cpu_count() or 1)
    pin = torch.cuda.is_available()

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=num_workers, pin_memory=pin)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False,
                              num_workers=num_workers, pin_memory=pin)

    # ── Model ─────────────────────────────────────────────────
    num_classes = len(CLASS_NAMES)
    model = create_model(num_classes).to(device)

    total_params     = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n[Model]   EfficientNet-B0  (pretrained = ImageNet)")
    print(f"          Classes:          {num_classes}")
    print(f"          Total params:     {total_params:>12,}")
    print(f"          Trainable params: {trainable_params:>12,}")

    # ── Loss / Optimiser / Scheduler ──────────────────────────
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(),
                                  lr=args.lr,
                                  weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=3,
    )
    early_stopping = EarlyStopping(patience=args.patience)

    # ── Ensure results dir exists ─────────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Persist split & class-name info ───────────────────────
    with open(RESULTS_DIR / "split_info.json", "w") as f:
        json.dump({
            "train_paths":  train_p,  "train_labels":  train_l,
            "val_paths":    val_p,    "val_labels":    val_l,
            "test_paths":   test_p,   "test_labels":   test_l,
        }, f, indent=2)

    with open(RESULTS_DIR / "class_names.json", "w") as f:
        json.dump(CLASS_NAMES, f, indent=2)

    # ── Training loop ─────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  TRAINING  —  {args.epochs} epoch(s),  bs={args.batch_size},  lr={args.lr}")
    print(f"{'=' * 60}\n")

    history = {
        "train_loss": [], "train_acc": [],
        "val_loss":   [], "val_acc":   [],
        "lr":         [],
    }
    best_val_acc = 0.0
    best_epoch   = 0
    t0           = time.time()

    for epoch in range(1, args.epochs + 1):
        lr_now = optimizer.param_groups[0]["lr"]
        print(f"Epoch {epoch}/{args.epochs}  (lr = {lr_now:.2e})")

        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device,
        )
        val_loss, val_acc = validate(model, val_loader, criterion, device)

        scheduler.step(val_loss)

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["lr"].append(lr_now)

        print(f"  Train  —  loss: {train_loss:.4f}   acc: {100 * train_acc:.2f}%")
        print(f"  Val    —  loss: {val_loss:.4f}   acc: {100 * val_acc:.2f}%")

        # ── Checkpoint best model ──
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch   = epoch
            torch.save({
                "epoch":            epoch,
                "model_state_dict": model.state_dict(),
                "val_accuracy":     val_acc,
                "val_loss":         val_loss,
                "class_names":      CLASS_NAMES,
                "num_classes":      num_classes,
            }, RESULTS_DIR / "best_model.pth")
            print(f"  >>> Best model saved  (val_acc = {100 * val_acc:.2f}%)")

        # ── Early stopping ──
        early_stopping(val_loss)
        if early_stopping.should_stop:
            print(f"\n  Early stopping triggered at epoch {epoch}")
            break

        print()

    elapsed = time.time() - t0

    # ── Persist history & config ──────────────────────────────
    with open(RESULTS_DIR / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    config = {
        "model":              "EfficientNet-B0",
        "pretrained":         "ImageNet",
        "image_size":         IMAGE_SIZE,
        "batch_size":         args.batch_size,
        "learning_rate":      args.lr,
        "weight_decay":       args.weight_decay,
        "optimizer":          "AdamW",
        "scheduler":          "ReduceLROnPlateau",
        "loss":               "CrossEntropyLoss",
        "epochs_requested":   args.epochs,
        "epochs_completed":   epoch,
        "best_epoch":         best_epoch,
        "best_val_accuracy":  best_val_acc,
        "early_stop_patience": args.patience,
        "seed":               args.seed,
        "device":             str(device),
        "gpu_name":           gpu_name,
        "training_seconds":   round(elapsed, 2),
        "num_train":          len(train_p),
        "num_val":            len(val_p),
        "num_test":           len(test_p),
    }
    with open(RESULTS_DIR / "training_config.json", "w") as f:
        json.dump(config, f, indent=2)

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  TRAINING COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Best epoch:          {best_epoch}")
    print(f"  Best val accuracy:   {100 * best_val_acc:.2f}%")
    print(f"  Time elapsed:        {elapsed:.1f}s")
    if torch.cuda.is_available():
        peak_mb = torch.cuda.max_memory_allocated(device) / (1024 ** 2)
        print(f"  Peak GPU memory:     {peak_mb:.1f} MB / {gpu_mem * 1024:.0f} MB")
    print(f"  Results saved to:    {RESULTS_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
