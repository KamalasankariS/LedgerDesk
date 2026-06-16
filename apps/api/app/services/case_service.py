"""Case business logic service."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AnalystAction, AuditEvent
from app.models.case import Case, CaseStatus, CaseStatusHistory
from app.schemas.audit import AnalystActionCreate

logger = structlog.get_logger()

# Valid status transitions
STATUS_TRANSITIONS = {
    "approve": {
        CaseStatus.AWAITING_REVIEW: CaseStatus.APPROVED,
        CaseStatus.SAFETY_CHECKED: CaseStatus.APPROVED,
    },
    "reject": {
        CaseStatus.AWAITING_REVIEW: CaseStatus.REJECTED,
        CaseStatus.SAFETY_CHECKED: CaseStatus.REJECTED,
    },
    "escalate": {
        CaseStatus.AWAITING_REVIEW: CaseStatus.ESCALATED,
        CaseStatus.SAFETY_CHECKED: CaseStatus.ESCALATED,
        CaseStatus.CREATED: CaseStatus.ESCALATED,
        CaseStatus.TRIAGED: CaseStatus.ESCALATED,
    },
    "reopen": {
        CaseStatus.APPROVED: CaseStatus.CREATED,
        CaseStatus.REJECTED: CaseStatus.CREATED,
        CaseStatus.COMPLETED: CaseStatus.CREATED,
    },
}


class CaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def transition_status(
        self, case: Case, new_status: CaseStatus, actor: str, reason: str | None = None
    ):
        old_status = case.status
        case.status = new_status

        history = CaseStatusHistory(
            case_id=case.id,
            from_status=old_status.value if old_status else None,
            to_status=new_status.value,
            changed_by=actor,
            reason=reason,
        )
        self.db.add(history)

        audit = AuditEvent(
            case_id=case.id,
            event_type="status_change",
            actor_type="human" if actor != "system" else "system",
            actor_id=actor,
            action=f"status_transition_{old_status.value}_to_{new_status.value}",
            resource_type="case",
            resource_id=str(case.id),
            details={
                "from": old_status.value,
                "to": new_status.value,
                "reason": reason,
            },
            trace_id=case.trace_id,
        )
        self.db.add(audit)

        logger.info(
            "case_status_changed",
            case_id=str(case.id),
            from_status=old_status.value,
            to_status=new_status.value,
        )

    async def perform_action(
        self, case: Case, action_in: AnalystActionCreate, analyst_id: uuid.UUID
    ) -> dict:
        action_type = action_in.action_type

        # Validate transition
        valid_transitions = STATUS_TRANSITIONS.get(action_type, {})
        new_status = valid_transitions.get(case.status)

        if action_type in ("approve", "reject", "escalate", "reopen") and not new_status:
            return {
                "success": False,
                "error": f"Cannot {action_type} a case in status '{case.status.value}'",
            }

        # Record the analyst action
        action = AnalystAction(
            case_id=case.id,
            analyst_id=analyst_id,
            recommendation_id=action_in.recommendation_id,
            action_type=action_type,
            reason=action_in.reason,
            metadata=action_in.metadata,
        )
        self.db.add(action)

        # Transition status if applicable
        if new_status:
            await self.transition_status(case, new_status, str(analyst_id), action_in.reason)

        # If approved, also mark as completed
        if action_type == "approve":
            await self.transition_status(
                case, CaseStatus.COMPLETED, str(analyst_id), "Approved and completed"
            )

        await self.db.flush()

        return {
            "success": True,
            "action_type": action_type,
            "new_status": case.status.value,
            "case_id": str(case.id),
        }
