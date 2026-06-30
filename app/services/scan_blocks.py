from __future__ import annotations

from dataclasses import dataclass

from app.models import Company


@dataclass(slots=True)
class ScanBlockPreview:
    company_id: int
    company_name: str
    current_block: int | None
    proposed_block: int


class ScanBlockAssignmentService:
    def preview_rebalance(
        self,
        companies: list[Company],
        *,
        total_blocks: int,
    ) -> list[ScanBlockPreview]:
        automatic_companies = [
            company for company in companies if company.scan_assignment_mode != "manual"
        ]
        sorted_companies = sorted(automatic_companies, key=lambda company: company.normalized_name)
        previews: list[ScanBlockPreview] = []
        for index, company in enumerate(sorted_companies):
            previews.append(
                ScanBlockPreview(
                    company_id=company.id,
                    company_name=company.name,
                    current_block=company.scan_block,
                    proposed_block=index % total_blocks,
                )
            )
        return previews

    def apply_rebalance(
        self, companies: list[Company], *, total_blocks: int
    ) -> list[ScanBlockPreview]:
        previews = self.preview_rebalance(companies, total_blocks=total_blocks)
        by_id = {company.id: company for company in companies}
        for preview in previews:
            company = by_id[preview.company_id]
            company.scan_block = preview.proposed_block
            company.scan_assignment_mode = "auto"
        return previews
