"""
Evaluation Module - AICIG Final System
Computes BLEU scores and manages user evaluation data.
"""

import re
import math
from collections import Counter
from typing import Optional


class Evaluator:
    """
    Provides quantitative evaluation of generated text outputs.

    Implements:
    - BLEU score (text quality vs reference)
    - Simple readability metrics
    - Prompt-relevance keyword scoring
    """

    # ── BLEU Score ────────────────────────────────────────────────────────────

    @staticmethod
    def tokenize(text: str) -> list:
        """Simple whitespace + punctuation tokenizer."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        return text.split()

    @staticmethod
    def ngrams(tokens: list, n: int) -> Counter:
        return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1))

    @classmethod
    def bleu_score(cls, hypothesis: str, reference: str, max_n: int = 4) -> float:
        """
        Compute BLEU-4 score between generated text and a reference.
        Returns score between 0.0 and 1.0.
        """
        hyp_tokens = cls.tokenize(hypothesis)
        ref_tokens = cls.tokenize(reference)

        if not hyp_tokens or not ref_tokens:
            return 0.0

        # Brevity penalty
        bp = min(1.0, math.exp(1 - len(ref_tokens) / max(len(hyp_tokens), 1)))

        precisions = []
        for n in range(1, max_n + 1):
            hyp_ngrams = cls.ngrams(hyp_tokens, n)
            ref_ngrams = cls.ngrams(ref_tokens, n)
            if not hyp_ngrams:
                precisions.append(0.0)
                continue
            clipped = sum(
                min(count, ref_ngrams[gram])
                for gram, count in hyp_ngrams.items()
            )
            precisions.append(clipped / sum(hyp_ngrams.values()))

        # Geometric mean with smoothing
        smoothed = [p if p > 0 else 1e-10 for p in precisions]
        log_avg = sum(math.log(p) for p in smoothed) / max_n
        return round(bp * math.exp(log_avg), 4)

    # ── Prompt relevance ─────────────────────────────────────────────────────

    @classmethod
    def prompt_relevance(cls, generated: str, prompt: str) -> float:
        """
        Simple keyword overlap score: what fraction of meaningful
        prompt words appear in the generated text.
        Returns 0.0 – 1.0.
        """
        stopwords = {
            "a","an","the","is","are","was","were","be","been","being",
            "have","has","had","do","does","did","will","would","shall",
            "should","may","might","must","can","could","of","in","to",
            "for","on","with","at","by","from","about","write","create",
            "generate","make","describe","explain","tell","give","me","i"
        }
        prompt_words = set(cls.tokenize(prompt)) - stopwords
        gen_words = set(cls.tokenize(generated))
        if not prompt_words:
            return 1.0
        overlap = len(prompt_words & gen_words) / len(prompt_words)
        return round(overlap, 4)

    # ── Readability ───────────────────────────────────────────────────────────

    @staticmethod
    def avg_sentence_length(text: str) -> float:
        """Average words per sentence."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0
        lengths = [len(s.split()) for s in sentences]
        return round(sum(lengths) / len(lengths), 1)

    @staticmethod
    def word_count(text: str) -> int:
        return len(text.split())

    # ── Combined report ───────────────────────────────────────────────────────

    @classmethod
    def evaluate(
        cls,
        generated: str,
        prompt: str,
        reference: Optional[str] = None,
    ) -> dict:
        """
        Return a full evaluation report for a generated text.
        """
        report = {
            "word_count": cls.word_count(generated),
            "avg_sentence_length": cls.avg_sentence_length(generated),
            "prompt_relevance": cls.prompt_relevance(generated, prompt),
        }
        if reference:
            report["bleu_score"] = cls.bleu_score(generated, reference)
        else:
            # Self-BLEU: use prompt as pseudo-reference for quick quality signal
            report["bleu_score"] = cls.bleu_score(generated, prompt)
        return report

    @staticmethod
    def format_report(report: dict) -> str:
        """Format evaluation report as readable string."""
        lines = ["📊 **Evaluation Report**"]
        lines.append(f"- Word count: {report.get('word_count', 'N/A')}")
        lines.append(f"- Avg sentence length: {report.get('avg_sentence_length', 'N/A')} words")
        rel = report.get('prompt_relevance', 0)
        lines.append(f"- Prompt relevance: {rel:.0%}")
        bleu = report.get('bleu_score', 0)
        lines.append(f"- BLEU score: {bleu:.4f}")
        return "\n".join(lines)
