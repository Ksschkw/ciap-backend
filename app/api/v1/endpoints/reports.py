from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas import ExportFormat
from app.dependencies import get_current_user
from app.dependencies import get_report_service
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{campaign_id}/export")
def export_report(
    campaign_id: UUID,
    export_format: ExportFormat = Query(default="pdf"),
    current_user: dict[str, str] = Depends(get_current_user),
    report_service: ReportService = Depends(get_report_service),
) -> dict[str, object]:
    return report_service.export_campaign_report(campaign_id, export_format=export_format)
