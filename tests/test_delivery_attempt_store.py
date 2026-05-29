from src.delivery_attempt_store import DeliveryAttemptStore


def make_store(tmp_path):
    return DeliveryAttemptStore(db_path=tmp_path / "supplier_collab.db")


def make_payload():
    return {
        "vendor": "Northstar Foods Co",
        "meeting_date": "2026-05-29",
        "briefing_id": "brief-123",
        "briefing_text": "Ready",
    }


def test_record_attempt_persists_row(tmp_path):
    store = make_store(tmp_path)

    row = store.record_attempt(
        briefing_id="brief-123",
        channel="slack",
        status="sent",
        attempt_count=1,
        payload=make_payload(),
        last_error="",
    )

    assert row["briefing_id"] == "brief-123"
    assert row["channel"] == "slack"
    assert row["status"] == "sent"
    assert row["attempt_count"] == 1
    assert row["payload"]["vendor"] == "Northstar Foods Co"
    assert row["created_at"].endswith("Z")
    assert row["updated_at"].endswith("Z")


def test_list_attempts_for_briefing_survives_new_store_instance(tmp_path):
    store = make_store(tmp_path)
    store.record_attempt("brief-123", "slack", "failed", 1, make_payload(), "timeout")
    store.record_attempt("brief-123", "slack", "sent", 2, make_payload(), "")
    store.record_attempt("other", "email", "sent", 1, make_payload(), "")

    rows = make_store(tmp_path).list_attempts(briefing_id="brief-123")

    assert [row["status"] for row in rows] == ["failed", "sent"]
    assert rows[0]["last_error"] == "timeout"


def test_list_attempts_without_filter_returns_all(tmp_path):
    store = make_store(tmp_path)
    store.record_attempt("brief-123", "slack", "sent", 1, make_payload(), "")
    store.record_attempt("brief-456", "email", "dead_letter", 3, make_payload(), "smtp")

    rows = store.list_attempts()

    assert len(rows) == 2
    assert {row["briefing_id"] for row in rows} == {"brief-123", "brief-456"}
