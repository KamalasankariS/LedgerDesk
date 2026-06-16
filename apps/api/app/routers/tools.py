"""Mock internal tool service endpoints."""

import json
import time
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent import ToolInvocation

logger = structlog.get_logger()
router = APIRouter()

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "sample_data"


def _load_json(subdir: str, filename: str) -> list:
    filepath = DATA_DIR / subdir / filename
    if filepath.exists():
        return json.loads(filepath.read_text())
    return []


TRANSACTIONS = None
ACCOUNTS = None
SETTLEMENTS = None
REFUNDS = None
MERCHANTS = None


def _get_data():
    global TRANSACTIONS, ACCOUNTS, SETTLEMENTS, REFUNDS, MERCHANTS
    if TRANSACTIONS is None:
        TRANSACTIONS = _load_json("transactions", "seed_transactions.json")
        ACCOUNTS = _load_json("accounts", "seed_accounts.json")
        SETTLEMENTS = _load_json("settlements", "seed_settlements.json")
        REFUNDS = _load_json("refunds", "seed_refunds.json")
        MERCHANTS = _load_json("merchants", "seed_merchants.json")
    return TRANSACTIONS, ACCOUNTS, SETTLEMENTS, REFUNDS, MERCHANTS


class ToolRequest(BaseModel):
    tool_name: str
    params: dict
    case_id: uuid.UUID | None = None


@router.post("/execute")
async def execute_tool(req: ToolRequest, db: AsyncSession = Depends(get_db)):
    start = time.time()
    trace_id = str(uuid.uuid4())

    transactions, accounts, settlements, refunds, merchants = _get_data()

    tool_handlers = {
        "get_transaction_timeline": _get_transaction_timeline,
        "get_account_activity": _get_account_activity,
        "get_settlement_status": _get_settlement_status,
        "get_refund_status": _get_refund_status,
        "search_similar_cases": _search_similar_cases,
        "get_merchant_reference": _get_merchant_reference,
    }

    handler = tool_handlers.get(req.tool_name)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {req.tool_name}")

    try:
        result = handler(req.params, transactions, accounts, settlements, refunds, merchants)
        status = "success"
        error = None
    except Exception as e:
        result = None
        status = "error"
        error = str(e)

    duration_ms = int((time.time() - start) * 1000)

    # Log tool invocation
    invocation = ToolInvocation(
        case_id=req.case_id,
        tool_name=req.tool_name,
        tool_type="read",
        input_params=req.params,
        output_data=result,
        status=status,
        error_message=error,
        duration_ms=duration_ms,
        trace_id=trace_id,
    )
    db.add(invocation)
    await db.flush()

    logger.info("tool_executed", tool=req.tool_name, status=status, duration_ms=duration_ms)

    return {
        "tool_name": req.tool_name,
        "status": status,
        "data": result,
        "error": error,
        "duration_ms": duration_ms,
        "trace_id": trace_id,
    }


def _get_transaction_timeline(params, transactions, *_):
    txn_id = params.get("transaction_id")
    if not txn_id:
        raise ValueError("transaction_id is required")

    account_txns = []
    target_acct = None
    for t in transactions:
        if t["transaction_id"] == txn_id:
            target_acct = t["account_id"]
            break

    if target_acct:
        account_txns = [t for t in transactions if t["account_id"] == target_acct]

    return {
        "transaction_id": txn_id,
        "timeline": sorted(account_txns, key=lambda x: x.get("authorization_date", "")),
        "total_transactions": len(account_txns),
    }


def _get_account_activity(params, transactions, accounts, *_):
    acct_id = params.get("account_id")
    if not acct_id:
        raise ValueError("account_id is required")

    account = next((a for a in accounts if a["account_id"] == acct_id), None)
    acct_txns = [t for t in transactions if t["account_id"] == acct_id]

    return {
        "account_id": acct_id,
        "account_info": account,
        "recent_transactions": sorted(
            acct_txns, key=lambda x: x.get("authorization_date", ""), reverse=True
        ),
        "transaction_count": len(acct_txns),
    }


def _get_settlement_status(params, _, __, settlements, *___):
    ref_id = params.get("reference_id") or params.get("transaction_id")
    if not ref_id:
        raise ValueError("reference_id or transaction_id is required")

    matches = [
        s
        for s in settlements
        if s.get("transaction_id") == ref_id or s.get("settlement_id") == ref_id
    ]
    return {
        "reference_id": ref_id,
        "settlements": matches,
        "found": len(matches) > 0,
    }


def _get_refund_status(params, *_, refunds, **__):
    ref_id = params.get("reference_id") or params.get("transaction_id")
    if not ref_id:
        raise ValueError("reference_id or transaction_id is required")

    matches = [
        r for r in refunds if r.get("original_transaction_id") == ref_id or r.get("arn") == ref_id
    ]
    return {
        "reference_id": ref_id,
        "refunds": matches,
        "found": len(matches) > 0,
    }


def _search_similar_cases(params, *_):
    return {
        "query": params,
        "similar_cases": [],
        "message": "Similar case search available after case history is populated",
    }


def _get_merchant_reference(params, *_, merchants=None):
    if merchants is None:
        merchants = []
    merchant_ref = params.get("merchant_ref") or params.get("merchant_id")
    if not merchant_ref:
        raise ValueError("merchant_ref or merchant_id is required")

    match = next((m for m in (merchants if isinstance(merchants, list) else [])), None)
    # Search through merchants list properly
    if isinstance(merchants, list):
        match = next(
            (
                m
                for m in merchants
                if m.get("merchant_id") == merchant_ref or merchant_ref in m.get("name", "")
            ),
            None,
        )

    return {
        "merchant_ref": merchant_ref,
        "merchant_info": match,
        "found": match is not None,
    }
