from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AudienceSegment:
    name: str
    share: float
    details: dict[str, Any]


@dataclass(slots=True)
class AudienceSegmenter:
    def segment(self, audience_snapshot: Mapping[str, Any]) -> list[AudienceSegment]:
        age_distribution = audience_snapshot.get("age_distribution", {})
        location_distribution = audience_snapshot.get("location_distribution", {})
        interest_tags = audience_snapshot.get("interest_tags", [])

        segments: list[AudienceSegment] = []
        if isinstance(age_distribution, Mapping):
            for label, share in sorted(age_distribution.items(), key=lambda item: item[1], reverse=True)[:3]:
                segments.append(AudienceSegment(name=f"age:{label}", share=float(share), details={"age_range": label}))
        if isinstance(location_distribution, Mapping):
            for label, share in sorted(location_distribution.items(), key=lambda item: item[1], reverse=True)[:3]:
                segments.append(AudienceSegment(name=f"location:{label}", share=float(share), details={"location": label}))
        if isinstance(interest_tags, list):
            for tag in interest_tags[:5]:
                segments.append(AudienceSegment(name=f"interest:{tag}", share=0.1, details={"interest_tag": tag}))

        return segments
