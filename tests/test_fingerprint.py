from app.detection.fingerprint import fingerprint_for_log, normalize_message
from app.models.schemas import LogEntry


def test_normalize_collapses_ids_and_numbers():
    a = normalize_message("payment timeout id=abc12345 order=99")
    b = normalize_message("payment timeout id=def67890 order=12")
    assert a == b


def test_fingerprint_groups_related_errors():
    e1 = LogEntry(level="ERROR", service="checkout", message="timeout id=aaa11111")
    e2 = LogEntry(level="ERROR", service="checkout", message="timeout id=bbb22222")
    assert fingerprint_for_log(e1) == fingerprint_for_log(e2)


def test_fingerprint_differs_by_service():
    e1 = LogEntry(level="ERROR", service="checkout", message="timeout")
    e2 = LogEntry(level="ERROR", service="payments", message="timeout")
    assert fingerprint_for_log(e1) != fingerprint_for_log(e2)
