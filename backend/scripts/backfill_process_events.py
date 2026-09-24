"""Run the conservative Phase 15C historical process-event backfill."""

from collections import Counter
from pathlib import Path
import sys

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal, engine
from app.services.process_event_backfill import backfill_process_events


BUSINESS_TABLES = (
    "assets",
    "asset_assignments",
    "incidents",
    "maintenances",
    "users",
    "technician_skills",
    "asset_histories",
)


def _counts(connection, tables):
    return {
        table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        for table in tables
    }


def main() -> None:
    with engine.connect() as connection:
        business_before = _counts(connection, BUSINESS_TABLES)
        process_before = _counts(connection, ("process_cases", "process_events"))

    with SessionLocal.begin() as db:
        report = backfill_process_events(db)
        business_during = _counts(db.connection(), BUSINESS_TABLES)
        if business_during != business_before:
            raise RuntimeError(
                f"Backfill changed business table counts: before={business_before}, after={business_during}"
            )
        process_during = _counts(db.connection(), ("process_cases", "process_events"))

    with engine.connect() as connection:
        business_after = _counts(connection, BUSINESS_TABLES)
        process_after = _counts(connection, ("process_cases", "process_events"))
        duplicate_keys = connection.execute(
            text(
                "SELECT count(*) FROM (SELECT source_event_key FROM process_events "
                "WHERE source_event_key IS NOT NULL GROUP BY source_event_key HAVING count(*) > 1) duplicates"
            )
        ).scalar_one()
        duplicate_sequences = connection.execute(
            text(
                "SELECT count(*) FROM (SELECT case_id, case_sequence FROM process_events "
                "GROUP BY case_id, case_sequence HAVING count(*) > 1) duplicates"
            )
        ).scalar_one()

    if business_after != business_before:
        raise RuntimeError(f"Business table counts changed: before={business_before}, after={business_after}")
    if duplicate_keys or duplicate_sequences:
        raise RuntimeError(
            f"Duplicate process data found: source_event_keys={duplicate_keys}, case_sequences={duplicate_sequences}"
        )

    event_counts = Counter(report["events_created"])
    print(f"Incident cases created: {report['incident_cases_created']}")
    print(f"Maintenance cases created: {report['maintenance_cases_created']}")
    print("Events created:")
    for event_type in (
        "INCIDENT_CREATED",
        "INCIDENT_STATUS_CHANGED",
        "TECHNICIAN_ASSIGNED",
        "MAINTENANCE_CREATED",
        "MAINTENANCE_STATUS_CHANGED",
    ):
        print(f"- {event_type}: {event_counts[event_type]}")
    print(f"Skipped incident status histories (no structured source): {report['incident_status_transitions_skipped']}")
    print(f"Skipped technician assignments (snapshot only): {report['technician_assignments_skipped']}")
    print(f"Skipped maintenance starts (no action timestamp): {report['maintenance_starts_skipped']}")
    print(f"Skipped maintenance completions (no proven prior start): {report['maintenance_completions_skipped']}")
    print(f"Business counts before/after: {business_before} / {business_after}")
    print(f"Process counts before/after: {process_before} / {process_during} / {process_after}")
    print(f"Duplicate source keys: {duplicate_keys}; duplicate case sequences: {duplicate_sequences}")


if __name__ == "__main__":
    main()
