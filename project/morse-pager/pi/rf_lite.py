# AI-assisted development (Claude Code, Anthropic)
"""
Lightweight Random Forest inference — no scikit-learn required.
Loads the exported JSON model and runs predictions using only numpy.
"""

import json

import numpy as np


class RFLite:
    """Minimal Random Forest classifier that loads from exported JSON."""

    def __init__(self, model_path: str):
        with open(model_path, "r") as f:
            data = json.load(f)

        self.n_classes = data["n_classes"]
        self.classes_ = np.array(data["classes"])
        self.trees = data["trees"]

    def _predict_tree(self, tree: dict, sample: np.ndarray) -> np.ndarray:
        """Traverse one decision tree, return class vote counts."""
        left = tree["children_left"]
        right = tree["children_right"]
        feature = tree["feature"]
        threshold = tree["threshold"]
        value = tree["value"]

        node = 0
        while left[node] != -1:  # -1 = leaf
            if sample[feature[node]] <= threshold[node]:
                node = left[node]
            else:
                node = right[node]

        return np.array(value[node])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities for each sample in X."""
        if X.ndim == 1:
            X = X.reshape(1, -1)

        results = np.zeros((X.shape[0], self.n_classes))

        for sample_idx in range(X.shape[0]):
            for tree in self.trees:
                votes = self._predict_tree(tree, X[sample_idx])
                results[sample_idx] += votes

        # Normalize each row to probabilities
        row_sums = results.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # avoid division by zero
        results /= row_sums

        return results

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels for each sample in X."""
        proba = self.predict_proba(X)
        return self.classes_[np.argmax(proba, axis=1)]
