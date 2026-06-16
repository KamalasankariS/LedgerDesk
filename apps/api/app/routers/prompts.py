"""Prompt version management endpoints."""

import difflib
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audit import PromptVersion

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def list_prompt_versions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PromptVersion).order_by(PromptVersion.agent_type, PromptVersion.version.desc())
    )
    versions = result.scalars().all()

    grouped: dict[str, list] = {}
    for v in versions:
        if v.agent_type not in grouped:
            grouped[v.agent_type] = []
        grouped[v.agent_type].append(
            {
                "id": str(v.id),
                "agent_type": v.agent_type,
                "version": v.version,
                "description": v.description,
                "is_active": v.is_active,
                "template_preview": v.template[:200] + "..."
                if len(v.template) > 200
                else v.template,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
        )
    return {"prompt_versions": grouped}


@router.get("/{version_id}")
async def get_prompt_version(version_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PromptVersion).where(PromptVersion.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    return {
        "id": str(version.id),
        "agent_type": version.agent_type,
        "version": version.version,
        "template": version.template,
        "description": version.description,
        "is_active": version.is_active,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@router.get("/active/{agent_type}")
async def get_active_prompt(agent_type: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.agent_type == agent_type, PromptVersion.is_active)
        .order_by(PromptVersion.version.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail=f"No active prompt for {agent_type}")
    return {
        "id": str(version.id),
        "agent_type": version.agent_type,
        "version": version.version,
        "template": version.template,
        "description": version.description,
    }


@router.get("/diff/{version_a_id}/{version_b_id}")
async def diff_prompt_versions(
    version_a_id: uuid.UUID,
    version_b_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result_a = await db.execute(select(PromptVersion).where(PromptVersion.id == version_a_id))
    result_b = await db.execute(select(PromptVersion).where(PromptVersion.id == version_b_id))
    va = result_a.scalar_one_or_none()
    vb = result_b.scalar_one_or_none()
    if not va or not vb:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    diff = list(
        difflib.unified_diff(
            va.template.splitlines(keepends=True),
            vb.template.splitlines(keepends=True),
            fromfile=f"{va.agent_type} v{va.version}",
            tofile=f"{vb.agent_type} v{vb.version}",
        )
    )
    return {
        "version_a": {
            "id": str(va.id),
            "agent_type": va.agent_type,
            "version": va.version,
        },
        "version_b": {
            "id": str(vb.id),
            "agent_type": vb.agent_type,
            "version": vb.version,
        },
        "diff": "".join(diff),
        "has_changes": len(diff) > 0,
    }
