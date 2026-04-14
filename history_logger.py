"""
History Logger - AICIG Final System
Tracks all generation sessions, outputs, ratings and metrics.
"""

import json
import os
from datetime import datetime
from typing import Optional


class HistoryLogger:
    """
    Logs every generation to a persistent JSON file.
    Supports retrieval, filtering, rating, and export.
    """

    def __init__(self, log_path: str = "generation_history.json"):
        self.log_path = log_path
        self.history = self._load()

    def _load(self) -> list:
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save(self):
        try:
            with open(self.log_path, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception:
            pass

    def log(
        self,
        generation_type: str,
        prompt: str,
        output: str,
        model: str,
        params: dict,
        metrics: dict,
    ) -> str:
        """Log a generation event and return its entry ID."""
        entry_id = f"gen_{len(self.history)+1:04d}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "type": generation_type,
            "prompt": prompt,
            "output": output,
            "model": model,
            "params": params,
            "metrics": metrics,
            "user_rating": None,
        }
        self.history.append(entry)
        self._save()
        return entry_id

    def get_history(self, n: int = 20) -> list:
        """Get last n history entries."""
        return self.history[-n:] if self.history else []

    def rate_last(self, rating: int) -> bool:
        """Rate the most recent entry."""
        if self.history:
            self.history[-1]["user_rating"] = rating
            self._save()
            return True
        return False

    def rate(self, entry_id: str, rating: int, feedback: str = "") -> bool:
        """Add a user rating (1-5) to a logged entry."""
        for entry in self.history:
            if entry["id"] == entry_id:
                entry["user_rating"] = max(1, min(5, rating))
                entry["user_feedback"] = feedback
                self._save()
                return True
        return False

    def get_recent(self, n: int = 10) -> list:
        return self.history[-n:][::-1]

    def get_stats(self) -> dict:
        if not self.history:
            return {"total": 0}
        rated = [e for e in self.history if e["user_rating"] is not None]
        avg_rating = (
            sum(e["user_rating"] for e in rated) / len(rated) if rated else None
        )
        type_counts = {}
        for e in self.history:
            type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1
        durations = [e["metrics"].get("time", 0) for e in self.history if e.get("metrics")]
        return {
            "total": len(self.history),
            "rated_count": len(rated),
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "by_type": type_counts,
            "avg_duration_seconds": round(sum(durations)/len(durations), 2) if durations else None,
        }

    def export_csv(self) -> str:
        """Export history as CSV string."""
        if not self.history:
            return "No history to export."
        headers = ["id", "timestamp", "type", "prompt", "output", "model",
                   "duration_seconds", "bleu", "user_rating"]
        lines = [",".join(headers)]
        for e in self.history:
            metrics = e.get("metrics", {})
            row = [
                str(e.get("id", "")),
                str(e.get("timestamp", "")),
                str(e.get("type", "")),
                f'"{str(e.get("prompt","")).replace(chr(34), chr(39))}"',
                f'"{str(e.get("output","")).replace(chr(34), chr(39))[:100]}"',
                str(e.get("model", "")),
                str(metrics.get("time", "")),
                str(metrics.get("bleu", "")),
                str(e.get("user_rating", "")),
            ]
            lines.append(",".join(row))
        return "\n".join(lines)
