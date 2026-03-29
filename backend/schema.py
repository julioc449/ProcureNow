from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class ComplianceObject(BaseModel):
    """
    Standard schema defining the contract between the AI Auditor and the UI.
    Each instance represents one requirement from the RFP and its compliance status.
    """
    category: str = Field(description="The category of the requirement, e.g., 'Safety', 'Insurance', 'Credentials'")
    requirement: str = Field(description="The exact requirement text extracted from the RFP")
    status: Literal["Complete", "Incomplete", "Partial"] = Field(
        description="The compliance status of the proposal against this requirement"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="AI confidence score (0.0-1.0) in the accuracy of this assessment"
    )
    proposal_evidence: Optional[str] = Field(
        None,
        description="Direct quote or summary from the proposal that supports the status determination"
    )
    missing_elements: List[str] = Field(
        default_factory=list,
        description="Specific items that are missing or need to be addressed"
    )
    page_reference: Optional[int] = Field(
        None,
        description="Page number in the proposal where the relevant evidence was found"
    )
    evidence_page: Optional[int] = Field(
        None,
        description="Exact page number cited from the routed proposal section"
    )
    format_match: Optional[bool] = Field(
        None,
        description="Whether the submission format matches the RFP-specified format (e.g. CSI vs Uniformat)"
    )
    percentage_filled: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="For Partial/Incomplete items, how much of this requirement has been addressed (0-100%)"
    )
    risk_level: Optional[Literal["Critical", "High", "Medium", "Low"]] = Field(
        None,
        description="Severity of the gap in terms of health, safety, and resource expenditure (Only for Partial/Incomplete)"
    )
    risk_reasoning: Optional[str] = Field(
        None,
        description="Justification for the assigned risk level"
    )


class RequirementItem(BaseModel):
    category: str = Field(description="The category of the requirement")
    requirement: str = Field(description="The exact requirement text from the RFP")


class RequirementList(BaseModel):
    """Schema for the Extractor module to output structured requirements from the RFP."""
    requirements: List[RequirementItem] = Field(
        description="List of all mandatory requirements extracted from the RFP document"
    )


class AuditReport(BaseModel):
    """
    Final output schema containing the full compliance audit.
    Includes per-requirement results and overall summary statistics.
    """
    proposal_id: str = Field(description="Identifier for the audited proposal")
    rfp_name: str = Field(default="", description="Name/title of the RFP document")
    audit_results: List[ComplianceObject] = Field(
        description="List of evaluated compliance objects, one per requirement"
    )
    critical_omissions: List[str] = Field(
        default_factory=list,
        description="High-priority issues that must be addressed before submission is compliant"
    )

    @property
    def total_requirements(self) -> int:
        return len(self.audit_results)

    @property
    def complete_count(self) -> int:
        return sum(1 for r in self.audit_results if r.status == "Complete")

    @property
    def partial_count(self) -> int:
        return sum(1 for r in self.audit_results if r.status == "Partial")

    @property
    def incomplete_count(self) -> int:
        return sum(1 for r in self.audit_results if r.status == "Incomplete")

    @property
    def overall_percentage(self) -> float:
        if not self.audit_results:
            return 0.0
        total = 0.0
        for r in self.audit_results:
            if r.status == "Complete":
                total += 100.0
            elif r.status == "Partial":
                total += r.percentage_filled
            # Incomplete contributes 0
        return round(total / len(self.audit_results), 1)

    def summary_dict(self) -> dict:
        """Returns summary stats for the frontend dashboard."""
        return {
            "proposal_id": self.proposal_id,
            "rfp_name": self.rfp_name,
            "total_requirements": self.total_requirements,
            "complete": self.complete_count,
            "partial": self.partial_count,
            "incomplete": self.incomplete_count,
            "overall_percentage": self.overall_percentage,
            "critical_omissions": self.critical_omissions,
            "audit_results": [r.model_dump() for r in self.audit_results],
        }
