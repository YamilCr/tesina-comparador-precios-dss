"""Auditable human decision for one proposed canonical product merge."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


REVIEW_TYPES = frozenset({"gtin_conflict", "semantic_alias"})
REVIEW_STATUSES = frozenset({"pending", "approved", "rejected"})


@dataclass
class ProductIdentityReview:
    id: UUID
    review_type: str
    source_product_id: UUID
    target_product_id: UUID
    evidence_value: str
    confidence: Decimal
    rationale: str
    status: str = "pending"
    decision_note: str | None = None
    created_at: datetime | None = None
    decided_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.review_type not in REVIEW_TYPES:
            raise ValueError(f"Invalid product identity review type: {self.review_type}.")
        if self.status not in REVIEW_STATUSES:
            raise ValueError(f"Invalid product identity review status: {self.status}.")
        if self.source_product_id == self.target_product_id:
            raise ValueError("Identity review products must be different.")
        if not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("Identity review confidence must be between 0 and 1.")
        if not self.evidence_value.strip() or not self.rationale.strip():
            raise ValueError("Identity review evidence and rationale are required.")
        self.evidence_value = self.evidence_value.strip()
        self.rationale = self.rationale.strip()
        self.decision_note = self.decision_note.strip() if self.decision_note else None

    def approve(self, note: str, decided_at: datetime) -> None:
        self._decide("approved", note, decided_at)

    def reject(self, note: str, decided_at: datetime) -> None:
        self._decide("rejected", note, decided_at)

    def _decide(self, status: str, note: str, decided_at: datetime) -> None:
        if self.status != "pending":
            raise ValueError("Only pending identity reviews can be decided.")
        if not note or not note.strip():
            raise ValueError("A decision note is required.")
        self.status = status
        self.decision_note = note.strip()
        self.decided_at = decided_at
