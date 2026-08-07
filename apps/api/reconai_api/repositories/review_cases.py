from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb


GOLDEN_CASE_ID = "review-golden-001"
GOLDEN_TENANT_ID = "00000000-0000-4000-8000-000000000001"


class ReviewCaseRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    def get_workflow_state(self, case_id: str = GOLDEN_CASE_ID) -> dict[str, Any] | None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, tenant_id, status, decision, comment, actor, decided_at, case_payload
                FROM review_cases
                WHERE id = %s
                """,
                (case_id,),
            )
            case = cursor.fetchone()
            if not case:
                return None

            cursor.execute(
                """
                SELECT actor, action, created_at, after_json
                FROM audit_events
                WHERE entity_type = 'review_case' AND entity_id = %s
                ORDER BY created_at ASC, action ASC
                """,
                (case_id,),
            )
            audit_events = cursor.fetchall()

        return {
            "id": case["id"],
            "tenant_id": str(case["tenant_id"]),
            "status": case["status"],
            "decision": case["decision"],
            "comment": case["comment"],
            "actor": case["actor"],
            "decided_at": _iso(case["decided_at"]),
            "case_payload": case["case_payload"],
            "audit_events": [
                {
                    "timestamp": _iso(event["created_at"]),
                    "actor": event["actor"],
                    "action": event["action"],
                    "details": (event["after_json"] or {}).get("details", ""),
                }
                for event in audit_events
            ],
        }

    def reset_golden_case(self, seed_audit_events: list[dict[str, str]]) -> None:
        with self.conn.transaction():
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO review_cases (id, tenant_id, status)
                    VALUES (%s, %s, 'REVIEW_REQUIRED')
                    ON CONFLICT (id) DO UPDATE SET
                      status = 'REVIEW_REQUIRED',
                      decision = NULL,
                      comment = NULL,
                      actor = NULL,
                      decided_at = NULL,
                      case_payload = NULL,
                      updated_at = now()
                    """,
                    (GOLDEN_CASE_ID, GOLDEN_TENANT_ID),
                )
                cursor.execute(
                    """
                    DELETE FROM audit_events
                    WHERE entity_type = 'review_case' AND entity_id = %s
                    """,
                    (GOLDEN_CASE_ID,),
                )
                self._insert_audit_events(cursor, seed_audit_events)

    def create_review_case(
        self,
        case_id: str,
        case_payload: dict[str, Any],
        seed_audit_events: list[dict[str, str]],
    ) -> None:
        with self.conn.transaction():
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO review_cases (id, tenant_id, status, case_payload)
                    VALUES (%s, %s, 'REVIEW_REQUIRED', %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                      status = 'REVIEW_REQUIRED',
                      decision = NULL,
                      comment = NULL,
                      actor = NULL,
                      decided_at = NULL,
                      case_payload = EXCLUDED.case_payload,
                      updated_at = now()
                    """,
                    (case_id, GOLDEN_TENANT_ID, Jsonb(case_payload)),
                )
                cursor.execute(
                    """
                    DELETE FROM audit_events
                    WHERE entity_type = 'review_case' AND entity_id = %s
                    """,
                    (case_id,),
                )
                self._insert_audit_events(cursor, seed_audit_events, case_id)

    def record_decision(
        self,
        decision: str,
        comment: str,
        actor: str,
        audit_details: str,
        case_id: str = GOLDEN_CASE_ID,
    ) -> None:
        status = "DISPUTED" if decision == "dispute" else "APPROVED"
        with self.conn.transaction():
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT status
                    FROM review_cases
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (case_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise ReviewCaseNotFound(case_id)
                if row["status"] != "REVIEW_REQUIRED":
                    raise ReviewCaseAlreadyDecided(row["status"])

                cursor.execute(
                    """
                    UPDATE review_cases
                    SET status = %s,
                        decision = %s,
                        comment = %s,
                        actor = %s,
                        decided_at = now(),
                        updated_at = now()
                    WHERE id = %s
                    """,
                    (status, decision, comment, actor, case_id),
                )
                self._insert_decision_audit_event(cursor, actor, audit_details, decision, status, case_id)

    def _insert_audit_events(
        self,
        cursor: Any,
        seed_audit_events: list[dict[str, str]],
        case_id: str = GOLDEN_CASE_ID,
    ) -> None:
        for event in seed_audit_events:
            cursor.execute(
                """
                INSERT INTO audit_events (
                  tenant_id, actor, action, entity_type, entity_id, after_json, created_at
                )
                VALUES (%s, %s, %s, 'review_case', %s, %s::jsonb, %s::timestamptz)
                """,
                (
                    GOLDEN_TENANT_ID,
                    event["actor"],
                    event["action"],
                    case_id,
                    Jsonb({"details": event["details"]}),
                    event["timestamp"],
                ),
            )

    def _insert_decision_audit_event(
        self,
        cursor: Any,
        actor: str,
        audit_details: str,
        decision: str,
        status: str,
        case_id: str = GOLDEN_CASE_ID,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO audit_events (
              tenant_id, actor, action, entity_type, entity_id, after_json
            )
            VALUES (%s, %s, 'review_decision_recorded', 'review_case', %s, %s::jsonb)
            """,
            (
                GOLDEN_TENANT_ID,
                actor,
                case_id,
                Jsonb({"details": audit_details, "decision": decision, "status": status}),
            ),
        )


class ReviewCaseAlreadyDecided(Exception):
    def __init__(self, status: str):
        self.status = status
        super().__init__(f"Review case already decided with status {status}.")


class ReviewCaseNotFound(Exception):
    pass


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
