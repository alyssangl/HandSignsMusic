"""
train_model.py
Train the number-sign classifier from data/landmarks.csv.

Run from the HandSignsMusic folder:
    python scripts/train_model.py
    python scripts/train_model.py --test-person amy    # test on someone the model never saw

What it does:
  1. Loads your recorded samples
  2. Splits them into TRAIN and TEST data (fairly - see below)
  3. Trains 3 different models and compares their accuracy
  4. Shows a report + confusion matrix for the best model
  5. Retrains the best model on ALL data and saves it to models/sign_model.joblib

Why the split is done "by burst":
  Samples inside one burst are almost identical (recorded within 2 seconds).
  If some went to training and some to testing, the test would be too easy
  and the accuracy would look better than it really is. So whole bursts are
  kept together: one burst per sign is held out for testing.
"""

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, ConfusionMatrixDisplay

import config

CSV_PATH = Path(config.DATA_DIR) / "landmarks.csv"
MODEL_PATH = Path(config.MODEL_DIR) / "sign_model.joblib"
CM_PATH = Path(config.MODEL_DIR) / "confusion_matrix.png"
FEATURES = [f"f{i}" for i in range(63)]


def load_data():
    rows = []
    with open(CSV_PATH, newline="") as f:
        for r in csv.DictReader(f):
            if r["label"] in config.SIGNS:          # ignore old labels (e.g. "8")
                rows.append(r)
    if not rows:
        raise SystemExit(f"No data found in {CSV_PATH}")
    X = np.array([[float(r[c]) for c in FEATURES] for r in rows], dtype=np.float32)
    y = np.array([r["label"] for r in rows])
    persons = np.array([r["person"] for r in rows])
    bursts = np.array([r["burst_id"] for r in rows])
    return X, y, persons, bursts


def split_by_burst(y, bursts, seed=42):
    """Hold out one whole burst per sign as test data."""
    rng = random.Random(seed)
    bursts_per_label = defaultdict(set)
    for label, b in zip(y, bursts):
        bursts_per_label[label].add(b)

    test_bursts = set()
    for label, bs in bursts_per_label.items():
        bs = sorted(bs)
        if len(bs) < 2:
            print(f"  Warning: sign '{label}' has only 1 burst, so it can't be tested fairly.")
            continue
        test_bursts.add(rng.choice(bs))
    test_mask = np.array([b in test_bursts for b in bursts])
    return ~test_mask, test_mask


def make_models():
    return {
        "Random Forest": RandomForestClassifier(n_estimators=300, random_state=42),
        "Neural Network (MLP)": make_pipeline(
            StandardScaler(),
            MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=1000, random_state=42),
        ),
        "SVM": make_pipeline(StandardScaler(), SVC(C=10, gamma="scale", probability=True, random_state=42)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-person", help="Test on this person's data only (they are left out of training)")
    args = parser.parse_args()

    X, y, persons, bursts = load_data()

    print("\nSamples per sign:")
    for s in config.SIGNS:
        print(f"  {s:>4} ({config.SIGN_NAMES[s]:<4}): {np.sum(y == s)}")
    print(f"People in dataset: {sorted(set(persons.tolist()))}")

    # ---------- Split ----------
    if args.test_person:
        test_mask = persons == args.test_person
        if not test_mask.any():
            raise SystemExit(f"No data for person '{args.test_person}'")
        train_mask = ~test_mask
        print(f"\nTest set = all data from '{args.test_person}' (never seen in training)")
    else:
        train_mask, test_mask = split_by_burst(y, bursts)
        print("\nTest set = one held-out burst per sign")
    print(f"Train samples: {train_mask.sum()} | Test samples: {test_mask.sum()}")

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    # ---------- Train & compare ----------
    print("\nTraining and comparing models...")
    results = {}
    for name, model in make_models().items():
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        results[name] = (acc, model)
        print(f"  {name:<22} accuracy: {acc * 100:.1f}%")

    best_name = max(results, key=lambda n: results[n][0])
    best_acc, best_model = results[best_name]
    print(f"\nBest model: {best_name} ({best_acc * 100:.1f}%)")

    # ---------- Detailed report ----------
    labels = [s for s in config.SIGNS if s in set(y)]
    display_names = [f"{s} ({config.SIGN_NAMES[s]})" for s in labels]
    y_pred = best_model.predict(X_test)
    print("\nPer-sign results (precision = how often a prediction is right,"
          " recall = how often the sign is found):")
    print(classification_report(y_test, y_pred, labels=labels, target_names=display_names, zero_division=0))

    Path(config.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 7))
    ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred, labels=labels, display_labels=display_names,
        cmap="Blues", ax=ax, colorbar=False,
    )
    ax.set_title(f"Confusion matrix - {best_name} ({best_acc * 100:.1f}%)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(CM_PATH, dpi=150)
    print(f"Confusion matrix saved to {CM_PATH}")

    # ---------- Final model on ALL data ----------
    final_model = make_models()[best_name]
    final_model.fit(X, y)
    joblib.dump({"model": final_model, "name": best_name, "labels": labels}, MODEL_PATH)
    print(f"Final model (trained on all data) saved to {MODEL_PATH}")

    plt.show()


if __name__ == "__main__":
    main()