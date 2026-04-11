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
        prompt: str,
        generation_type: str,  # "text", "image", "combined"
        text_output: Optional[str],
        image_generated: bool,
        text_model: str,
        image_model: str,
        params: dict,
        duration_seconds: float,
        bleu_score: Optional[float] = None,
    ) -> str:
        """Log a generation event and return its entry ID."""
        entry_id = f"gen_{len(self.history)+1:04d}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "type": generation_type,
            "text_output": text_output,
            "image_generated": image_generated,
            "text_model": text_model,
            "image_model": image_model,
            "params": params,
            "duration_seconds": round(duration_seconds, 2),
            "bleu_score": bleu_score,
            "user_rating": None,
            "user_feedback": None,
        }
        self.history.append(entry)
        self._save()
        return entry_id

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
        durations = [e["duration_seconds"] for e in self.history if e.get("duration_seconds")]
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
        headers = ["id", "timestamp", "type", "prompt", "text_model",
                   "image_model", "duration_seconds", "bleu_score", "user_rating"]
        lines = [",".join(headers)]
        for e in self.history:
            row = [
                str(e.get("id", "")),
                str(e.get("timestamp", "")),
                str(e.get("type", "")),
                f'"{e.get("prompt","").replace(chr(34), chr(39))}"',
                str(e.get("text_model", "")),
                str(e.get("image_model", "")),
                str(e.get("duration_seconds", "")),
                str(e.get("bleu_score", "")),
                str(e.get("user_rating", "")),
            ]
            lines.append(",".join(row))
        return "\n".join(lines)
