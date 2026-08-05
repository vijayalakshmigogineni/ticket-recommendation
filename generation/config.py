"""Config-file-driven generation targets. See config/generation_config.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunConfig(StrictModel):
    name: str
    model: str = "qwen3:4b"
    host: str = "http://localhost:11434"  # local Ollama server, no API key
    max_concurrent_requests: int = 4
    max_regeneration_attempts: int = 3


class RangeConfig(StrictModel):
    avg: float
    min: int
    max: int


class ScaleConfig(StrictModel):
    customers: int
    tickets_per_customer: RangeConfig
    messages_per_ticket: RangeConfig
    eval_queries: int


class StatusSplitConfig(StrictModel):
    non_terminal: float
    terminal: float


class StyleConfig(StrictModel):
    tone: dict[str, float]
    length_bucket: dict[str, float]
    noise_level: dict[str, float]


class DistributionsConfig(StrictModel):
    category_weights: dict[str, float]
    category_floor: int
    status_split: StatusSplitConfig
    difficulty_tier_weights: dict[str, float]
    style: StyleConfig
    disambiguation_customers_min: int

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> "DistributionsConfig":
        for label, weights in (
            ("category_weights", self.category_weights),
            ("difficulty_tier_weights", self.difficulty_tier_weights),
            ("style.tone", self.style.tone),
            ("style.length_bucket", self.style.length_bucket),
            ("style.noise_level", self.style.noise_level),
        ):
            total = sum(weights.values())
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"{label} weights must sum to 1.0, got {total}")
        return self


class PathsConfig(StrictModel):
    state_db: str
    output_dir: str


class GenerationConfig(StrictModel):
    run: RunConfig
    scale: ScaleConfig
    distributions: DistributionsConfig
    paths: PathsConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> "GenerationConfig":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)
