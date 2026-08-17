"""HTTP request contracts for bounded security investigations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InvestigationRequest(BaseModel):
    """A user question for one already-authorized audit session."""

    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=4000)
