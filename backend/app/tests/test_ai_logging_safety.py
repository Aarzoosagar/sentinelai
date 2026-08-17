from app.core.config.settings import get_settings
from app.services.ai import observability


def test_structured_logs_redact_sensitive_fields_and_default_is_safe(caplog):
    assert get_settings().ai_log_sensitive_data is False
    with caplog.at_level("INFO", logger="sentinelai.ai"):
        observability.record("safe_event", api_key="gsk_fake_secret", authorization="Bearer fake", detail="JWT_SECRET_KEY=fake-value")
    output = caplog.text
    assert "gsk_fake_secret" not in output
    assert "Bearer fake" not in output
    assert "fake-value" not in output
