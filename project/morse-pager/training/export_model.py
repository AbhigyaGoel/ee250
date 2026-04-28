# AI-assisted development (Claude Code, Anthropic)
"""
Export trained RandomForest to a lightweight JSON format that can be
loaded on the Pi without scikit-learn. Only needs numpy for inference.
"""

import json
import os

import joblib


def extract_tree(tree):
    """Extract a single DecisionTree into plain lists."""
    t = tree.tree_
    return {
        "children_left": t.children_left.tolist(),
        "children_right": t.children_right.tolist(),
        "feature": t.feature.tolist(),
        "threshold": t.threshold.tolist(),
        "value": t.value.squeeze().tolist(),  # shape (n_nodes, n_classes)
    }


def main():
    model_path = os.path.join(os.path.dirname(__file__), "..", "pi", "model", "rf_classifier.joblib")
    clf = joblib.load(model_path)

    forest = {
        "n_classes": int(clf.n_classes_),
        "classes": clf.classes_.tolist(),
        "trees": [extract_tree(est) for est in clf.estimators_],
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "pi", "model", "rf_forest.json")
    with open(out_path, "w") as f:
        json.dump(forest, f)

    size_kb = os.path.getsize(out_path) / 1024
    print(f"Exported {len(forest['trees'])} trees to {out_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
