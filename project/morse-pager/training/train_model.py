"""
Train a Random Forest classifier on synthetic Morse code timing data.

Reads training_data.csv, trains a RandomForestClassifier, evaluates accuracy,
saves the joblib model (for laptop use), and exports a lightweight JSON
version (for Pi — no sklearn needed).
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

LABEL_NAMES = ["dot", "dash", "intra_letter_gap", "inter_letter_gap", "word_gap"]
FEATURE_COLS = ["raw_duration_ms", "norm_by_session_mean", "relative_ratio", "is_tap"]


def main():
    data_path = os.path.join(os.path.dirname(__file__), "training_data.csv")
    if not os.path.exists(data_path):
        print("training_data.csv not found. Run generate_data.py first.")
        return

    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} samples")

    X = df[FEATURE_COLS].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    print("Training Random Forest...")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=LABEL_NAMES))

    accuracy = np.mean(y_pred == y_test)
    print(f"Overall accuracy: {accuracy:.4f}")

    # Feature importances
    print("\nFeature importances:")
    for name, imp in zip(FEATURE_COLS, clf.feature_importances_):
        print(f"  {name}: {imp:.4f}")

    # Save joblib model (for laptop / re-export)
    model_dir = os.path.join(os.path.dirname(__file__), "..", "pi", "model")
    os.makedirs(model_dir, exist_ok=True)
    joblib_path = os.path.join(model_dir, "rf_classifier.joblib")
    joblib.dump(clf, joblib_path)
    print(f"\nJoblib model saved to {joblib_path}")

    # Export lightweight JSON for Pi (no sklearn needed to load)
    json_path = os.path.join(model_dir, "rf_forest.json")
    export_rf_to_json(clf, json_path)
    size_kb = os.path.getsize(json_path) / 1024
    print(f"JSON model saved to {json_path} ({size_kb:.0f} KB)")


def export_rf_to_json(clf, output_path: str):
    """Serialize a sklearn RandomForestClassifier to JSON for rf_lite.py."""
    trees = []
    for estimator in clf.estimators_:
        t = estimator.tree_
        trees.append({
            "children_left": t.children_left.tolist(),
            "children_right": t.children_right.tolist(),
            "feature": t.feature.tolist(),
            "threshold": t.threshold.tolist(),
            "value": t.value[:, 0, :].tolist(),
        })
    model_data = {
        "n_classes": int(clf.n_classes_),
        "classes": clf.classes_.tolist(),
        "trees": trees,
    }
    with open(output_path, "w") as f:
        json.dump(model_data, f)


if __name__ == "__main__":
    main()
