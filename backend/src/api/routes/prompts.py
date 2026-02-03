"""API routes for prompt versioning and A/B testing management.

Provides endpoints for:
- Viewing prompt versions and metrics
- Managing A/B tests
- Comparing version performance
- Manual rollback
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.llm.prompt_versioning import (
    PromptType,
    prompt_version_manager,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])


# =============================================================================
# Request/Response Models
# =============================================================================


class VersionCreate(BaseModel):
    """Request to create a new prompt version."""

    prompt_type: str = Field(..., description="Type of prompt (e.g., injury_analysis)")
    template: str = Field(..., description="Prompt template with placeholders")
    description: str = Field(..., description="Description of this version")
    version_suffix: str | None = Field(None, description="Optional version suffix")


class ABTestStart(BaseModel):
    """Request to start an A/B test."""

    prompt_type: str = Field(..., description="Type of prompt to test")
    version_weights: dict[str, float] = Field(
        ..., description="Version IDs and their traffic weights (e.g., {'v1': 0.5, 'v2': 0.5})"
    )
    duration_days: int | None = Field(None, description="Test duration in days (None for indefinite)")


class VersionMetrics(BaseModel):
    """Metrics for a prompt version."""

    version_id: str
    sample_count: int
    accuracy: float
    avg_brier_score: float
    avg_latency_ms: float


class VersionComparison(BaseModel):
    """Comparison of version metrics."""

    version_id: str
    is_baseline: bool
    sample_count: int
    accuracy: float
    avg_brier_score: float
    avg_latency_ms: float
    accuracy_vs_baseline: float | None = None
    brier_vs_baseline: float | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/types")
async def list_prompt_types() -> list[str]:
    """List all available prompt types."""
    return [pt.value for pt in PromptType]


@router.get("/versions")
async def list_versions(
    prompt_type: str | None = Query(None, description="Filter by prompt type"),
) -> list[dict[str, Any]]:
    """List all registered prompt versions."""
    if prompt_type:
        try:
            pt = PromptType(prompt_type)
            versions = prompt_version_manager.get_versions(pt)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")
    else:
        # Get all versions across all types
        versions = []
        for pt in PromptType:
            versions.extend(prompt_version_manager.get_versions(pt))

    return [
        {
            "version_id": v.version_id,
            "prompt_type": v.prompt_type.value,
            "description": v.description,
            "is_active": v.is_active,
            "is_baseline": v.is_baseline,
            "template_hash": v.template_hash,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]


@router.get("/versions/{version_id}")
async def get_version(version_id: str) -> dict[str, Any]:
    """Get details of a specific prompt version."""
    version = prompt_version_manager.get_version(version_id)

    if not version:
        raise HTTPException(status_code=404, detail=f"Version not found: {version_id}")

    return {
        "version_id": version.version_id,
        "prompt_type": version.prompt_type.value,
        "template": version.template,
        "description": version.description,
        "is_active": version.is_active,
        "is_baseline": version.is_baseline,
        "template_hash": version.template_hash,
        "created_at": version.created_at.isoformat(),
    }


@router.post("/versions")
async def create_version(request: VersionCreate) -> dict[str, Any]:
    """Create a new prompt version."""
    try:
        pt = PromptType(request.prompt_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid prompt type: {request.prompt_type}")

    version = prompt_version_manager.create_version(
        prompt_type=pt,
        template=request.template,
        description=request.description,
        version_suffix=request.version_suffix,
    )

    return {
        "version_id": version.version_id,
        "prompt_type": version.prompt_type.value,
        "message": f"Created version {version.version_id}",
    }


@router.get("/metrics/{version_id}")
async def get_version_metrics(version_id: str) -> VersionMetrics:
    """Get metrics for a specific prompt version."""
    metrics = prompt_version_manager.get_metrics(version_id)

    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics found for: {version_id}")

    return VersionMetrics(
        version_id=metrics.version_id,
        sample_count=metrics.sample_count,
        accuracy=metrics.accuracy,
        avg_brier_score=metrics.avg_brier_score,
        avg_latency_ms=metrics.avg_latency_ms,
    )


@router.get("/compare/{prompt_type}")
async def compare_versions(prompt_type: str) -> list[VersionComparison]:
    """Compare all versions of a prompt type."""
    try:
        pt = PromptType(prompt_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")

    comparison = prompt_version_manager.compare_versions(pt)

    return [
        VersionComparison(
            version_id=data["version_id"],
            is_baseline=data["is_baseline"],
            sample_count=data["sample_count"],
            accuracy=data["accuracy"],
            avg_brier_score=data["avg_brier_score"],
            avg_latency_ms=data["avg_latency_ms"],
            accuracy_vs_baseline=data.get("accuracy_vs_baseline"),
            brier_vs_baseline=data.get("brier_vs_baseline"),
        )
        for data in comparison.values()
    ]


# =============================================================================
# A/B Testing Endpoints
# =============================================================================


@router.get("/ab-tests")
async def list_ab_tests() -> list[dict[str, Any]]:
    """List all active A/B tests."""
    tests = []
    for pt in PromptType:
        ab_test = prompt_version_manager.get_ab_test(pt)
        if ab_test:
            tests.append({
                "prompt_type": ab_test.prompt_type.value,
                "version_weights": ab_test.version_weights,
                "start_time": ab_test.start_time.isoformat(),
                "end_time": ab_test.end_time.isoformat() if ab_test.end_time else None,
                "min_samples_per_version": ab_test.min_samples_per_version,
            })
    return tests


@router.post("/ab-tests")
async def start_ab_test(request: ABTestStart) -> dict[str, Any]:
    """Start a new A/B test."""
    try:
        pt = PromptType(request.prompt_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid prompt type: {request.prompt_type}")

    # Validate version weights
    for version_id in request.version_weights:
        if not prompt_version_manager.get_version(version_id):
            raise HTTPException(status_code=400, detail=f"Version not found: {version_id}")

    try:
        config = prompt_version_manager.start_ab_test(
            prompt_type=pt,
            version_weights=request.version_weights,
            duration_days=request.duration_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": f"Started A/B test for {request.prompt_type}",
        "prompt_type": config.prompt_type.value,
        "version_weights": config.version_weights,
        "end_time": config.end_time.isoformat() if config.end_time else None,
    }


@router.delete("/ab-tests/{prompt_type}")
async def stop_ab_test(prompt_type: str) -> dict[str, Any]:
    """Stop an active A/B test."""
    try:
        pt = PromptType(prompt_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")

    stopped = prompt_version_manager.stop_ab_test(pt)

    if not stopped:
        raise HTTPException(status_code=404, detail=f"No A/B test found for: {prompt_type}")

    return {"message": f"Stopped A/B test for {prompt_type}"}


@router.post("/ab-tests/{prompt_type}/check-rollback")
async def check_rollback(prompt_type: str) -> dict[str, Any]:
    """Check if rollback is needed based on performance."""
    try:
        pt = PromptType(prompt_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")

    rollback_to = prompt_version_manager.check_rollback_needed(pt)

    return {
        "prompt_type": prompt_type,
        "rollback_needed": rollback_to is not None,
        "rollback_to": rollback_to,
    }


@router.post("/ab-tests/{prompt_type}/rollback")
async def perform_rollback(prompt_type: str) -> dict[str, Any]:
    """Manually rollback to baseline version."""
    try:
        pt = PromptType(prompt_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid prompt type: {prompt_type}")

    success = prompt_version_manager.rollback_to_baseline(pt)

    if not success:
        raise HTTPException(status_code=400, detail=f"No A/B test to rollback for: {prompt_type}")

    baseline = prompt_version_manager.get_baseline_version(pt)

    return {
        "message": f"Rolled back {prompt_type} to baseline",
        "baseline_version": baseline.version_id if baseline else None,
    }


# =============================================================================
# State Management
# =============================================================================


@router.get("/state/export")
async def export_state() -> dict[str, Any]:
    """Export current prompt versioning state."""
    return prompt_version_manager.export_state()


@router.post("/state/import")
async def import_state(state: dict[str, Any]) -> dict[str, Any]:
    """Import prompt versioning state."""
    imported = prompt_version_manager.import_state(state)
    return {"message": f"Imported {imported} items"}
