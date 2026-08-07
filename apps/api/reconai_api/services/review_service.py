from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import HTTPException

from ..demo_data import GOLDEN_REVIEW_CASE
from ..repositories.review_cases import (
    GOLDEN_CASE_ID,
    ReviewCaseAlreadyDecided,
    ReviewCaseNotFound,
    ReviewCaseRepository,
)


class ReviewService:
    def __init__(self, repository: ReviewCaseRepository):
        self.repository = repository

    def get_golden_case(self) -> dict[str, Any]:
        workflow_state = self.repository.get_workflow_state(GOLDEN_CASE_ID)
        if workflow_state is None:
            self.reset_golden_case()
            workflow_state = self.repository.get_workflow_state(GOLDEN_CASE_ID)
        if workflow_state is None:
            raise HTTPException(status_code=500, detail="Golden review case was not seeded.")
        if not workflow_state["audit_events"] and workflow_state["status"] == "REVIEW_REQUIRED":
            self.reset_golden_case()
            workflow_state = self.repository.get_workflow_state(GOLDEN_CASE_ID)
            if workflow_state is None:
                raise HTTPException(status_code=500, detail="Golden review case was not seeded.")
        return _merge_case(workflow_state)

    def apply_decision(self, decision: str, comment: str) -> dict[str, Any]:
        normalized_comment = comment.strip()
        if len(normalized_comment) < 3:
            raise HTTPException(status_code=422, detail="Review comment must be at least 3 characters.")
        self._ensure_seeded()

        try:
            self.repository.record_decision(
                decision=decision,
                comment=normalized_comment,
                actor="demo_reviewer",
                audit_details=f"{decision}: {normalized_comment}",
            )
        except ReviewCaseAlreadyDecided as exc:
            raise HTTPException(
                status_code=409,
                detail=f"Review case already decided with status {exc.status}.",
            ) from exc
        except ReviewCaseNotFound as exc:
            raise HTTPException(status_code=404, detail="Review case not found.") from exc

        return self.get_golden_case()

    def reset_golden_case(self) -> dict[str, Any]:
        self.repository.reset_golden_case(deepcopy(GOLDEN_REVIEW_CASE["audit_events"]))
        workflow_state = self.repository.get_workflow_state(GOLDEN_CASE_ID)
        if workflow_state is None:
            raise HTTPException(status_code=500, detail="Golden review case reset failed.")
        return _merge_case(workflow_state)

    def _ensure_seeded(self) -> None:
        workflow_state = self.repository.get_workflow_state(GOLDEN_CASE_ID)
        needs_seed_timeline = (
            workflow_state is not None
            and not workflow_state["audit_events"]
            and workflow_state["status"] == "REVIEW_REQUIRED"
        )
        if workflow_state is None or needs_seed_timeline:
            self.repository.reset_golden_case(deepcopy(GOLDEN_REVIEW_CASE["audit_events"]))


def _merge_case(workflow_state: dict[str, Any]) -> dict[str, Any]:
    case = deepcopy(GOLDEN_REVIEW_CASE)
    case["status"] = workflow_state["status"]
    case["audit_events"] = workflow_state["audit_events"]
    if workflow_state["decision"]:
        case["review_decision"] = {
            "decision": workflow_state["decision"],
            "comment": workflow_state["comment"],
            "actor": workflow_state["actor"],
        }
    else:
        case.pop("review_decision", None)
    return case
