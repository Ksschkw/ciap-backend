from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_POSITIVE_TERMS = {
    "love",
    "great",
    "amazing",
    "awesome",
    "excellent",
    "nice",
    "good",
    "fantastic",
    "beautiful",
    "inspiring",
}
_NEGATIVE_TERMS = {
    "bad",
    "terrible",
    "awful",
    "hate",
    "poor",
    "worst",
    "boring",
    "ugly",
    "spam",
    "fake",
}


@dataclass(slots=True)
class SentimentAnalysisResult:
    score: float
    label: str
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    dominant_sentiment: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SentimentAnalyzer:
    positive_terms: set[str] = field(default_factory=lambda: set(_POSITIVE_TERMS))
    negative_terms: set[str] = field(default_factory=lambda: set(_NEGATIVE_TERMS))

    def analyze_text(self, text: str) -> SentimentAnalysisResult:
        normalized = text.lower()
        positive_hits = sum(1 for term in self.positive_terms if term in normalized)
        negative_hits = sum(1 for term in self.negative_terms if term in normalized)
        total_hits = positive_hits + negative_hits

        if total_hits == 0:
            return SentimentAnalysisResult(
                score=0.0,
                label="neutral",
                positive_ratio=0.0,
                negative_ratio=0.0,
                neutral_ratio=1.0,
                dominant_sentiment="neutral",
            )

        score = (positive_hits - negative_hits) / total_hits
        positive_ratio = positive_hits / total_hits
        negative_ratio = negative_hits / total_hits
        neutral_ratio = max(0.0, 1.0 - (positive_ratio + negative_ratio))
        label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
        dominant = "positive" if positive_ratio > negative_ratio else "negative" if negative_ratio > positive_ratio else "neutral"

        return SentimentAnalysisResult(
            score=round(score, 3),
            label=label,
            positive_ratio=round(positive_ratio, 3),
            negative_ratio=round(negative_ratio, 3),
            neutral_ratio=round(neutral_ratio, 3),
            dominant_sentiment=dominant,
            details={"positive_hits": positive_hits, "negative_hits": negative_hits},
        )

    def analyze_comments(self, comments: list[str]) -> dict[str, Any]:
        if not comments:
            return {
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "neutral_ratio": 1.0,
                "dominant_sentiment": "neutral",
            }

        results = [self.analyze_text(comment) for comment in comments]
        positive_ratio = sum(result.positive_ratio for result in results) / len(results)
        negative_ratio = sum(result.negative_ratio for result in results) / len(results)
        neutral_ratio = max(0.0, 1.0 - positive_ratio - negative_ratio)
        dominant = "positive" if positive_ratio > negative_ratio else "negative" if negative_ratio > positive_ratio else "neutral"
        return {
            "positive_ratio": round(positive_ratio, 3),
            "negative_ratio": round(negative_ratio, 3),
            "neutral_ratio": round(neutral_ratio, 3),
            "dominant_sentiment": dominant,
        }
