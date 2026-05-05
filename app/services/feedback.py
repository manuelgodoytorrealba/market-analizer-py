import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.entities import Listing, ListingFeedback

FEEDBACK_LABELS = (
    "match_ok",
    "wrong_product",
    "accessory_only",
    "damaged",
    "locked",
    "parts_only",
    "unclear",
)


def save_listing_feedback(
    db: Session,
    *,
    listing: Listing,
    feedback_label: str,
    feedback_notes: str = "",
) -> ListingFeedback:
    normalized_label = _normalize_feedback_label(feedback_label)
    normalized_notes = (feedback_notes or "").strip()
    existing = (
        db.query(ListingFeedback)
        .filter(ListingFeedback.listing_id == listing.id)
        .first()
    )

    if existing is None:
        feedback = ListingFeedback(
            listing_id=int(listing.id),
            source=str(listing.source),
            external_id=str(listing.external_id),
            title=str(listing.title),
            normalized_name=str(listing.normalized_name or ""),
            search_query=str(listing.search_query or ""),
            feedback_label=normalized_label,
            feedback_notes=normalized_notes,
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback

    existing.source = str(listing.source)
    existing.external_id = str(listing.external_id)
    existing.title = str(listing.title)
    existing.normalized_name = str(listing.normalized_name or "")
    existing.search_query = str(listing.search_query or "")
    existing.feedback_label = normalized_label
    existing.feedback_notes = normalized_notes
    db.commit()
    db.refresh(existing)
    return existing


def get_listing_feedback(
    db: Session,
    *,
    listing_id: int,
) -> ListingFeedback | None:
    return (
        db.query(ListingFeedback)
        .filter(ListingFeedback.listing_id == listing_id)
        .first()
    )


def build_feedback_dataset_rows(db: Session) -> list[dict]:
    feedback_rows = (
        db.query(ListingFeedback)
        .order_by(ListingFeedback.updated_at.desc(), ListingFeedback.id.desc())
        .all()
    )
    return [_feedback_row_to_dataset(row) for row in feedback_rows]


def export_feedback_dataset(db: Session, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_feedback_dataset_rows(db)

    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return path


def feedback_targets(feedback_label: str) -> dict[str, bool | None]:
    normalized_label = _normalize_feedback_label(feedback_label)
    if normalized_label == "match_ok":
        return {
            "is_target_match": True,
            "is_damaged_or_parts_only": False,
        }
    if normalized_label in {"wrong_product", "accessory_only"}:
        return {
            "is_target_match": False,
            "is_damaged_or_parts_only": False,
        }
    if normalized_label in {"damaged", "locked", "parts_only"}:
        return {
            "is_target_match": True,
            "is_damaged_or_parts_only": True,
        }
    return {
        "is_target_match": None,
        "is_damaged_or_parts_only": None,
    }


def _feedback_row_to_dataset(row: ListingFeedback) -> dict:
    targets = feedback_targets(row.feedback_label)
    text = " ".join(
        value
        for value in [
            row.title,
            row.normalized_name,
            row.search_query,
        ]
        if value
    ).strip()
    return {
        "text": text,
        "title": row.title,
        "normalized_name": row.normalized_name or "",
        "search_query": row.search_query or "",
        "source": row.source,
        "external_id": row.external_id,
        "feedback_label": row.feedback_label,
        "feedback_notes": row.feedback_notes or "",
        "targets": targets,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _normalize_feedback_label(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in FEEDBACK_LABELS:
        raise ValueError(f"Unsupported feedback label: {value}")
    return normalized
