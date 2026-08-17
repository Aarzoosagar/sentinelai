"""
Per-finding AI features: narrative explanations and IaC/CLI remediation
snippets. Explanations are cached on `Finding.ai_explanation` after the
first request so repeat views of the same finding don't re-call Groq.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.prompts.templates import finding_explanation_prompt, iac_example_prompt
from app.services.ai import groq_client
from app.services.ai.serializers import finding_to_dict

_VALID_IAC_FORMATS = {"cli", "terraform", "cloudformation"}


def get_or_generate_explanation(db: Session, finding: Finding) -> tuple[str, bool]:
    """Returns (explanation_text, generated_fresh)."""
    if finding.ai_explanation:
        return finding.ai_explanation, False

    messages = finding_explanation_prompt(finding_to_dict(finding))
    explanation = groq_client.complete(messages, task="explain_finding")

    finding.ai_explanation = explanation
    db.add(finding)
    db.flush()
    return explanation, True


def generate_iac_example(finding: Finding, iac_format: str) -> str:
    if iac_format not in _VALID_IAC_FORMATS:
        raise ValueError(f"iac_format must be one of {_VALID_IAC_FORMATS}, got '{iac_format}'")

    messages = iac_example_prompt(finding_to_dict(finding), iac_format)
    return groq_client.complete(messages, task="iac_generation")
