"""Pipeline stage definitions — stage names, order, and progress weights.

Each stage is weighted proportionally so the sum of all weights equals 100,
representing 100% pipeline completion.
"""

from __future__ import annotations

from enum import StrEnum


class PipelineStage(StrEnum):
    """Ordered stages of the recalibration pipeline."""

    INGEST = "ingest"
    PEER_BASELINES = "peer_baselines"
    Z_SCORES = "z_scores"
    SEED_SCORING = "seed_scoring"
    PROVIDER_PROFILES = "provider_profiles"
    ML_SCORING = "ml_scoring"


# Weight of each stage as a percentage of total pipeline progress.
# Weights must sum to 100.
STAGE_WEIGHTS: dict[PipelineStage, int] = {
    PipelineStage.INGEST: 20,
    PipelineStage.PEER_BASELINES: 15,
    PipelineStage.Z_SCORES: 10,
    PipelineStage.SEED_SCORING: 10,
    PipelineStage.PROVIDER_PROFILES: 25,
    PipelineStage.ML_SCORING: 20,
}

# Ordered list of all stages (for iteration)
ORDERED_STAGES: list[PipelineStage] = [
    PipelineStage.INGEST,
    PipelineStage.PEER_BASELINES,
    PipelineStage.Z_SCORES,
    PipelineStage.SEED_SCORING,
    PipelineStage.PROVIDER_PROFILES,
    PipelineStage.ML_SCORING,
]
