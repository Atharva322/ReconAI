from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|dispute)$")
    comment: str = Field(min_length=3, max_length=500)
