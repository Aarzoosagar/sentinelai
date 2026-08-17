"""
Single source of truth for Groq model configuration.

The project rule is "support configurable Groq models through one
configuration file" — every AI service call must import its model/params
from here rather than hard-coding a model string inline.
"""

from dataclasses import dataclass

from app.core.config.settings import get_settings


@dataclass(frozen=True)
class GroqRuntimeConfig:
    api_key: str
    model: str
    timeout_seconds: int
    max_retries: int
    temperature: float
    max_tokens: int


# Models known to work well for each task type. The active model for each
# task defaults to the global GROQ_MODEL env var but can be overridden here
# without touching any service code.
TASK_MODEL_OVERRIDES: dict[str, str | None] = {
    "explain_finding": None,       # None => use settings.groq_model
    "chat": None,
    "executive_summary": None,
    "compliance_summary": None,
    "iac_generation": None,        # Terraform/CloudFormation snippet generation
}


def get_groq_config(task: str | None = None) -> GroqRuntimeConfig:
    """
    Build the runtime Groq config for a given task. Falls back to the
    globally configured model when no task-specific override is set.
    """
    settings = get_settings()
    model = settings.groq_model
    if task is not None:
        override = TASK_MODEL_OVERRIDES.get(task)
        if override:
            model = override

    return GroqRuntimeConfig(
        api_key=settings.groq_api_key,
        model=model,
        timeout_seconds=settings.groq_timeout_seconds,
        max_retries=settings.groq_max_retries,
        temperature=settings.groq_temperature,
        max_tokens=settings.groq_max_tokens,
    )
