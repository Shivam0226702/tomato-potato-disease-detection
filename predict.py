#!/usr/bin/env python3
"""
predict.py — Predict the disease class of a single leaf image.

Usage
-----
    python predict.py path/to/leaf.jpg
    python predict.py path/to/leaf.jpg --top-k 5
"""

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Union, Tuple, List, Dict, Any

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
#  REUSABLE INFERENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def get_device() -> torch.device:
    """Return CUDA device if available, otherwise CPU."""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def get_transform() -> transforms.Compose:
    """Return deterministic image preprocessing transform (matching val/test)."""
    return transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def load_class_names(results_dir: Path = RESULTS_DIR) -> List[str]:
    """Load class names list from results directory."""
    class_names_file = results_dir / "class_names.json"
    if not class_names_file.exists():
        raise FileNotFoundError(
            f"Class names file not found: {class_names_file}. "
            "Please run train.py first."
        )
    with open(class_names_file, "r") as f:
        return json.load(f)


def create_model(num_classes: int) -> nn.Module:
    """Instantiate EfficientNet-B0 architecture with custom linear head."""
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def load_model(
    model_path: Union[str, Path] = None,
    class_names: List[str] = None,
    device: torch.device = None,
) -> nn.Module:
    """Load trained EfficientNet-B0 checkpoint and set to eval mode."""
    if device is None:
        device = get_device()
    if class_names is None:
        class_names = load_class_names()
    if model_path is None:
        model_path = RESULTS_DIR / "best_model.pth"

    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model checkpoint not found: {model_path}. "
            "Please run train.py first."
        )

    model = create_model(len(class_names)).to(device)
    checkpoint = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model


def parse_class_name(class_name: str) -> Tuple[str, str]:
    """
    Parse raw class name string into (crop, disease).
    e.g.:
        'Tomato___Early_blight' -> ('Tomato', 'Early Blight')
        'Potato___Healthy'      -> ('Potato', 'Healthy')
        'Potato___Late_blight'  -> ('Potato', 'Late Blight')
    """
    if "___" in class_name:
        crop, disease = class_name.split("___", 1)
        disease_clean = disease.replace("_", " ").title()
        return crop, disease_clean
    return "Unknown", class_name.replace("_", " ").title()


def predict_image(
    image_input: Union[str, Path, Image.Image, io.BytesIO],
    model: nn.Module = None,
    class_names: List[str] = None,
    device: torch.device = None,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Predict crop and disease for an input image.

    Args:
        image_input: File path (str/Path), PIL Image, or file-like stream
        model: Loaded model instance (loaded automatically if None)
        class_names: List of class labels (loaded automatically if None)
        device: Torch device (resolved automatically if None)
        top_k: Number of top predictions to return

    Returns:
        dict with keys:
            - predicted_class: str
            - crop: str
            - disease: str
            - confidence: float (0.0 to 1.0)
            - top_predictions: list of dicts
    """
    if device is None:
        device = get_device()
    if class_names is None:
        class_names = load_class_names()
    if model is None:
        model = load_model(class_names=class_names, device=device)

    # Load PIL image
    if isinstance(image_input, (str, Path)):
        img_path = Path(image_input)
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {img_path}")
        image = Image.open(img_path)
    elif isinstance(image_input, Image.Image):
        image = image_input
    elif hasattr(image_input, "read"):
        image = Image.open(image_input)
    else:
        raise ValueError(f"Unsupported image input type: {type(image_input)}")

    # Preprocess
    image = image.convert("RGB")
    transform = get_transform()
    tensor = transform(image).unsqueeze(0).to(device)

    # Inference
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]

    k = min(top_k, len(class_names))
    top_probs, top_indices = probs.topk(k)

    top_predictions = []
    for rank in range(k):
        idx = top_indices[rank].item()
        prob = float(top_probs[rank].item())
        cls_name = class_names[idx]
        crop, disease = parse_class_name(cls_name)
        top_predictions.append({
            "class_name": cls_name,
            "crop": crop,
            "disease": disease,
            "confidence": prob,
        })

    best = top_predictions[0]
    return {
        "predicted_class": best["class_name"],
        "crop": best["crop"],
        "disease": best["disease"],
        "confidence": best["confidence"],
        "top_predictions": top_predictions,
    }


# ═══════════════════════════════════════════════════════════════════════
#  CLI
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

    try:
        results = predict_image(image_path, top_k=args.top_k)
    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        sys.exit(1)

    print(f"\nPrediction for: {image_path.name}")
    print("=" * 50)
    for rank, item in enumerate(results["top_predictions"]):
        tag = "  <-- predicted" if rank == 0 else ""
        print(f"  {item['class_name']:<30} {100 * item['confidence']:>6.2f}%{tag}")
    print("=" * 50)
    print(f"Crop:    {results['crop']}")
    print(f"Disease: {results['disease']}")
    print(f"Score:   {results['confidence'] * 100:.2f}%")


if __name__ == "__main__":
    main()
