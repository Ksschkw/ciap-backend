from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas import ExportFormat
from app.dependencies import get_current_user
from app.dependencies import get_report_service
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{campaign_id}/export", summary="Export Campaign Report", response_description="Downloadable report file URL or binary data")
def export_report(
    campaign_id: UUID,
    export_format: ExportFormat = Query(default="pdf", description="Format to export: pdf or csv"),
    current_user: dict[str, str] = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
) -> dict[str, object]:
    """
    Generate and export a comprehensive report for a specific campaign.
    
    The frontend can trigger this to allow SMEs to download campaign performance metrics.
    Currently supports PDF generation.
    """
    return report_service.export_campaign_report(campaign_id, export_format=export_format)
