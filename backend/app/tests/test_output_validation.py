import pytest

from app.services.ai.guardrails.output import OutputValidationError, protect_chat_output, validate_top_risks


def test_top_risks_requires_strict_schema_and_authorized_finding_ids():
    valid = {"top_risks": [{"finding_id": "fnd-1", "title": "Public bucket", "reason": "Internet access"}]}
    assert validate_top_risks(valid, ["fnd-1"]) == valid["top_risks"]
    with pytest.raises(OutputValidationError):
        validate_top_risks({"top_risks": [{"finding_id": "foreign", "title": "x", "reason": "x"}]}, ["fnd-1"])
    with pytest.raises(OutputValidationError):
        validate_top_risks({"top_risks": [{"finding_id": "fnd-1", "title": "x", "reason": "x", "extra": "no"}]}, ["fnd-1"])


def test_chat_output_redacts_secrets_and_removes_unsupported_finding_citations():
    answer = "JWT_SECRET_KEY=test-secret-key-not-for-production-use-only-in-pytest. Finding ID foreign-finding is severe. Finding ID fnd-safe is valid."
    protected = protect_chat_output(answer, ["fnd-safe"])
    assert "test-secret-key-not-for-production-use-only-in-pytest" not in protected
    assert "foreign-finding" not in protected
    assert "Finding ID fnd-safe" in protected
