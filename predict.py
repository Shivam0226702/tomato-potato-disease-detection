#!/usr/bin/env python3
"""
predict.py — Predict the disease class of a single leaf image.

Usage
-----
    python predict.py path/to/leaf.jpg
    python predict.py path/to/leaf.jpg --top-k 5
"""

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image


# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURATION  (mirrors train.py constants)
# ═══════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR  = PROJECT_ROOT / "results"

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]
IMAGE_SIZE    = 224


# ═══════════════════════════════════════════════════════════════════════
#  MODEL  (same architecture as train.py — weights loaded from checkpoint)
# ═══════════════════════════════════════════════════════════════════════

def create_model(num_classes: int):
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Predict plant disease from a leaf image"
    )
    parser.add_argument("image", type=str, help="Path to a leaf image (.jpg/.png)")
    parser.add_argument("--top-k", type=int, default=3,
                        help="Show top-K predictions (default: 3)")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)

    # ── Load class names ──────────────────────────────────────
    class_names_file = RESULTS_DIR / "class_names.json"
    model_file       = RESULTS_DIR / "best_model.pth"

    for p in (class_names_file, model_file):
        if not p.exists():
            print(f"[ERROR] Missing file: {p}")
            print("        Run train.py first to generate results.")
            sys.exit(1)

    with open(class_names_file) as f:
        class_names = json.load(f)

    # ── Device ────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ── Load model ────────────────────────────────────────────
    model = create_model(len(class_names)).to(device)
    checkpoint = torch.load(model_file, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # ── Preprocess (deterministic — same as val/test) ─────────
    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

    image  = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0).to(device)

    # ── Predict ───────────────────────────────────────────────
    with torch.no_grad():
        logits = model(tensor)
        probs  = torch.softmax(logits, dim=1)[0]

    top_k = min(args.top_k, len(class_names))
    top_probs, top_indices = probs.topk(top_k)

    # ── Display results ───────────────────────────────────────
    print(f"\nPrediction for: {image_path.name}")
    print("=" * 50)
    for rank in range(top_k):
        idx  = top_indices[rank].item()
        prob = top_probs[rank].item()
        tag  = "  <-- predicted" if rank == 0 else ""
        print(f"  {class_names[idx]:<30} {100 * prob:>6.2f}%{tag}")
    print("=" * 50)


if __name__ == "__main__":
    main()
