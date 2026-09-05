#!/usr/bin/env python3
"""
evaluate.py — Evaluate the best saved model on the held-out test set.

Usage
-----
    python evaluate.py

Outputs (saved to results/):
    - test_results.json        per-class precision / recall / F1 + accuracy
    - confusion_matrix.png     heatmap visualisation
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix

import matplotlib
matplotlib.use("Agg")            # headless backend — works without a display
import matplotlib.pyplot as plt
import seaborn as sns


# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURATION  (mirrors train.py constants)
# ═══════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR  = PROJECT_ROOT / "results"

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]
IMAGE_SIZE    = 224


# ═══════════════════════════════════════════════════════════════════════
#  DATASET & MODEL  (minimal duplicates from train.py for standalone use)
# ═══════════════════════════════════════════════════════════════════════

class PlantDiseaseDataset(Dataset):
    """Map-style dataset identical to the one used during training."""

    def __init__(self, image_paths, labels, transform=None):
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


def create_model(num_classes: int):
    """Instantiate EfficientNet-B0 *without* pretrained weights (we load our own)."""
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    # ── Load metadata from training run ───────────────────────
    class_names_path = RESULTS_DIR / "class_names.json"
    split_info_path  = RESULTS_DIR / "split_info.json"
    model_path       = RESULTS_DIR / "best_model.pth"

    for p in (class_names_path, split_info_path, model_path):
        if not p.exists():
            print(f"[ERROR] Missing file: {p}")
            print("        Run train.py first to generate results.")
            sys.exit(1)

    with open(class_names_path) as f:
        class_names = json.load(f)

    with open(split_info_path) as f:
        split = json.load(f)

    test_paths  = split["test_paths"]
    test_labels = split["test_labels"]
    num_classes = len(class_names)

    print(f"[Test set]  {len(test_paths)} images  ·  {num_classes} classes")

    # ── Device ────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Device]    {device}" +
          (f"  —  {torch.cuda.get_device_name(0)}" if device.type == "cuda" else ""))

    # ── DataLoader ────────────────────────────────────────────
    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

    test_ds = PlantDiseaseDataset(test_paths, test_labels, transform=transform)
    num_workers = 0 if sys.platform == "win32" else min(4, os.cpu_count() or 1)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False,
                             num_workers=num_workers,
                             pin_memory=torch.cuda.is_available())

    # ── Load trained model ────────────────────────────────────
    model = create_model(num_classes).to(device)
    checkpoint = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    print(f"[Model]     Loaded from epoch {checkpoint['epoch']}  "
          f"(val_acc = {100 * checkpoint['val_accuracy']:.2f}%)")

    # ── Inference ─────────────────────────────────────────────
    model.eval()
    all_preds  = []
    all_labels = []

    with torch.no_grad():
        for images, labels in test_loader:
            images  = images.to(device)
            outputs = model(images)
            _, preds = outputs.max(1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)

    # ── Metrics ───────────────────────────────────────────────
    accuracy = (all_preds == all_labels).mean()

    print(f"\n{'=' * 60}")
    print(f"  TEST RESULTS  —  Accuracy: {100 * accuracy:.2f}%")
    print(f"{'=' * 60}\n")

    report_str = classification_report(
        all_labels, all_preds, target_names=class_names, digits=4,
    )
    print(report_str)

    # ── Confusion matrix ─────────────────────────────────────
    cm = confusion_matrix(all_labels, all_preds)

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=class_names, yticklabels=class_names, ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"Confusion Matrix  —  Test Accuracy: {100 * accuracy:.2f}%")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()

    cm_path = RESULTS_DIR / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=150)
    plt.close(fig)
    print(f"[Saved]  Confusion matrix → {cm_path}")

    # ── Persist JSON results ──────────────────────────────────
    report_dict = classification_report(
        all_labels, all_preds, target_names=class_names,
        digits=4, output_dict=True,
    )
    test_results = {
        "accuracy":              float(accuracy),
        "classification_report": report_dict,
        "confusion_matrix":      cm.tolist(),
        "num_test_images":       len(test_paths),
    }

    results_path = RESULTS_DIR / "test_results.json"
    with open(results_path, "w") as f:
        json.dump(test_results, f, indent=2)
    print(f"[Saved]  Test results    → {results_path}")


if __name__ == "__main__":
    main()
