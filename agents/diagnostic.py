
import logging
import time
from typing import Optional

from pydantic import BaseModel, Field

from agents import tools
from agents.llm import get_llm
from backend.models import DiagnosisResult


log = logging.getLogger(__name__)

HEALTHY = {
    "VPN": {"up"},
    "Account": {"active"},
    "Disk": {"ok"},
}

MAX_ATTEMPTS = 2

SYSTEM_PROMPT = """You are the Diagnostic Agent of an IT helpdesk system.
You are given a support ticket and the raw status returned by the monitoring system for the
relevant service. Decide the probable cause and which single fix, if any, should be attempted.

Allowed fixes for this service: {allowed}

Rules:
- Base your answer ONLY on the ticket and the raw status. Do not invent facts.
- Choose a fix only if the status shows a problem it can plausibly solve.
- If the cause needs human action (expired certificate, account disabled by HR, hardware
  fault, unknown state), set recommended_action to null.
- The probable_cause must be directly supported by the raw status.
- Do not speculate about underlying technical causes that the
  monitoring system has not identified.
- Do not use assumptions such as overloaded servers, network
  misconfiguration, hardware faults or configuration errors unless
  explicitly established by the ticket or raw status.
- If the raw status says cause is gateway_timeout, describe it as
  a VPN gateway timeout. Do not speculate about why it occurred.
- Prefer a short, evidence-based explanation over a detailed
  speculative explanation.
- probable_cause: one short sentence a technician would understand."""


class _LLMDiagnosis(BaseModel):
    probable_cause: str = Field(
        description="One short sentence"
    )

    recommended_action: Optional[str] = Field(
        default=None,
        description="One allowed fix, or null if none applies"
    )


def _get_chain():
    return get_llm().with_structured_output(_LLMDiagnosis)


# ---------- Helpers ----------

def _check_human_intervention_needed(description: str) -> Optional[tuple[str, str]]:
    """Detect specific failure causes in ticket text that strictly require human administrative intervention."""
    desc = description.lower()

    if any(k in desc for k in (
        "certificate expired", "expired certificate", "cert expired",
        "certificate error", "cert error", "expired cert", "certificate has expired"
    )):
        return (
            "cert_expired",
            "Client SSL/VPN certificate has expired and requires manual re-issuance by an IT administrator."
        )

    if any(k in desc for k in (
        "disabled by hr", "hr disabled", "hr suspension",
        "account deactivated by hr", "hr hold"
    )):
        return (
            "disabled_by_hr",
            "Account access restricted by HR department policy; requires HR administrative authorization."
        )

    return None


def _status_of(service: str, raw: dict) -> str:
    if raw.get("error") == "not_found":
        return "user_not_found"

    return (
        raw.get("level")
        if service == "Disk"
        else raw.get("status", "unknown")
    )


def _rule_based(
    service: str,
    status: str,
    raw: dict
) -> tuple[str, Optional[str]]:

    """Safety net used when the LLM fails or answers with something invalid."""

    if service == "VPN":
        cause = raw.get("cause") or "unknown VPN fault"
        return (
            f"VPN is {status}: {cause}",
            "reset_vpn" if raw.get("fixable") else None
        )

    if service == "Account":
        if status == "locked":
            return (
                "Account locked after repeated failed logins",
                "unlock_account"
            )

        if status == "password_expired":
            return (
                "Password has expired",
                "reset_password"
            )

        return (
            f"Account state '{status}' needs human review",
            None
        )

    if service == "Disk":
        return (
            f"Disk usage at {raw.get('usage_percent')}% ({status})",
            "cleanup_disk"
        )

    return "Unknown fault", None


def _collect_status(service: str, username: str) -> dict:
    if service == "VPN":
        return tools.check_vpn()

    if service == "Account":
        return tools.check_account(username)

    return tools.check_disk()


def _ask_llm(
    service: str,
    description: str,
    raw: dict
) -> Optional[_LLMDiagnosis]:

    allowed = tools.ALLOWED_ACTIONS[service]

    messages = [
        ("system", SYSTEM_PROMPT.format(allowed=allowed)),
        (
            "human",
            f"Ticket: {description}\n\nService: {service}\nRaw status: {raw}"
        ),
    ]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            out = _get_chain().invoke(messages)

            if isinstance(out, dict):
                out = _LLMDiagnosis(**out)

            if out is not None:
                return out

        except Exception as e:
            log.warning(
                "Diagnostic LLM attempt %d failed: %s",
                attempt,
                e
            )

            # Avoid retrying when the Gemini quota is exhausted.
            error_text = str(e).lower()

            if any(
                term in error_text
                for term in ("resource_exhausted", "429", "quota")
            ):
                log.error("Gemini quota issue. Stopping retries.")
                break

            if attempt < MAX_ATTEMPTS:
                time.sleep(2)

    return None


# ---------- Main entry point ----------

def run_diagnosis(
    category: str,
    username: str,
    description: str
) -> DiagnosisResult:

    """Never raises. Returns a DiagnosisResult describing what was found."""

    if category not in tools.ALLOWED_ACTIONS:
        return DiagnosisResult(
            service="none",
            service_status="not_applicable",
            probable_cause=(
                "Issue is outside the supported services (VPN, Account, Disk)"
            ),
            recommended_action=None
        )

    try:
        raw = _collect_status(category, username)

    except tools.BackendUnreachable as e:
        return DiagnosisResult(
            service=category,
            service_status="unreachable",
            probable_cause=str(e),
            recommended_action=None
        )

    status = _status_of(category, raw)

    # Detect explicit unfixable issues requiring human intervention (e.g., certificate renewal, HR lock)
    human_needed = _check_human_intervention_needed(description)
    if human_needed:
        override_status, override_cause = human_needed
        return DiagnosisResult(
            service=category,
            service_status=override_status,
            details=raw,
            probable_cause=override_cause,
            recommended_action=None
        )

    if status in HEALTHY[category]:
        return DiagnosisResult(
            service=category,
            service_status=status,
            details=raw,
            probable_cause=(
                "No fault detected on the service; "
                "issue may be on the user's side"
            ),
            recommended_action=None
        )

    if status == "user_not_found":
        return DiagnosisResult(
            service=category,
            service_status=status,
            details=raw,
            probable_cause=f"No account found for username '{username}'",
            recommended_action=None
        )

    # Use the rule-based result as a safety net.
    fallback_cause, fallback_action = _rule_based(
        category,
        status,
        raw
    )

    llm = _ask_llm(category, description, raw)

    cause, action = fallback_cause, fallback_action

    if llm is not None:
        cause = llm.probable_cause or fallback_cause
        action = llm.recommended_action

        # Use the safe rule-based action if the LLM
        # returns no action or recommends an invalid action.
        if action not in tools.ALLOWED_ACTIONS[category]:
            action = fallback_action

    return DiagnosisResult(
        service=category,
        service_status=status,
        details=raw,
        probable_cause=cause,
        recommended_action=action
    )

