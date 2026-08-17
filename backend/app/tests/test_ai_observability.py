import pytest

from app.services.ai import observability


def test_timing_records_success_failure_latency_and_correlation():
    observability.reset_metrics()
    tokens = observability.set_correlation("request-1", "audit-1")
    try:
        with observability.timed("test_llm", counter="llm_requests", model="safe-model"):
            pass
        with pytest.raises(RuntimeError):
            with observability.timed("test_tool", counter="tool_calls", tool_name="get_findings"):
                raise RuntimeError("failure")
    finally:
        observability.reset_correlation(tokens)
    metrics = observability.metrics_snapshot()
    assert metrics["counters"]["llm_requests_total"] == 1
    assert metrics["counters"]["tool_calls_errors_total"] == 1
    assert metrics["latencies"]["llm_requests_latency_ms"]


def test_error_classifier_distinguishes_authorization_and_validation():
    class ToolAuthorizationError(Exception): pass
    class ToolValidationError(Exception): pass
    assert observability.classify_error(ToolAuthorizationError()) == "authorization_error"
    assert observability.classify_error(ToolValidationError()) == "validation_error"
