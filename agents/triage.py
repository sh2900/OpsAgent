
import logging
import time

from agents.llm import get_llm
from backend.models import TriageResult


log = logging.getLogger(__name__)

FALLBACK_MARKER = "Automatic triage failed"

SYSTEM_PROMPT = """You are the Ticket Triage Agent of an enterprise IT helpdesk system.
Your job is to analyze incoming employee support tickets and classify their CATEGORY and URGENCY with high accuracy.

=== CATEGORY CLASSIFICATION ===
Choose exactly one category based on the underlying technical issue:

1. VPN:
   - Remote access, VPN connections, client errors, tunnel establishment, SSL certificates, gateways, or inability to reach internal company servers/networks while working remotely, from home, or traveling.

2. Account:
   - Logins, passwords, credentials, locked accounts, expired passwords, disabled/suspended accounts, single sign-on (SSO), MFA/2FA authentication failures, account permissions, or password policy questions.

3. Disk:
   - Hard drive full, low storage warnings, out of disk space, temporary file buildup, disk cleanup requests, or inability to save files/install updates specifically due to insufficient storage.

4. Other:
   - Any issue outside VPN, Account, or Disk. Examples: printers, Wi-Fi/office internet, monitors, hardware peripherals, software bugs, email/Outlook, or general requests.

=== URGENCY CLASSIFICATION ===
Choose exactly one urgency level following standard ITIL criteria:

- High:
  The employee is completely blocked from working (e.g., account locked, password expired, cannot connect to VPN/internal resources with no workaround), essential files cannot be saved, multiple people are affected, or an imminent deadline is threatened.

- Medium:
  Partial disruption or degraded performance (e.g., slow connection, intermittent disconnects, single non-critical portal failing, employee can still perform other work).

- Low:
  General inquiries, routine access requests, policy questions, or non-blocking warnings with no current impact on work.

=== FEW-SHOT EXAMPLES ===
Ticket: "I can't connect to the VPN from home, it keeps timing out"
Category: VPN | Urgency: High | Reasoning: Remote access connection failure completely blocking remote access to company systems.

Ticket: "VPN is very slow today but I can still work"
Category: VPN | Urgency: Medium | Reasoning: Performance degradation but employee can still perform work.

Ticket: "I'm locked out of my account after entering the wrong password several times"
Category: Account | Urgency: High | Reasoning: Account is locked out, preventing employee from logging in to work.

Ticket: "How often do I need to change my password?"
Category: Account | Urgency: Low | Reasoning: General informational question regarding password policy without work disruption.

Ticket: "Disk full error, I can't save my presentation for the meeting"
Category: Disk | Urgency: High | Reasoning: Storage exhaustion preventing user from saving essential work files.

Ticket: "Getting a warning that my C: drive has 15% space remaining"
Category: Disk | Urgency: Low | Reasoning: Advisory storage warning without any current failure or disruption.

Ticket: "The office printer on the 2nd floor is out of paper and jamming"
Category: Other | Urgency: Medium | Reasoning: Hardware printer fault affecting office document printing.

Ticket: "Can't log into the HR portal, it says authentication failed"
Category: Account | Urgency: Medium | Reasoning: Single application login failure while general system access remains available.

Provide your classification with a concise one-sentence reasoning based on the ticket details."""

MAX_ATTEMPTS = 2


def _get_chain():
    """Create a chain with structured LLM output."""
    return get_llm().with_structured_output(TriageResult)


def _is_quota_error(error: Exception) -> bool:
    """Identify quota and rate-limit errors that should not be retried."""
    error_text = str(error).lower()

    return any(
        term in error_text
        for term in ("resource_exhausted", "429", "quota")
    )


def fallback_result(reason: str) -> TriageResult:
    """Return a safe fallback when automatic triage fails."""

    return TriageResult(
        category="Other",
        urgency="Medium",
        reasoning=(
            f"{FALLBACK_MARKER} ({reason}); "
            "routed for human review."
        )
    )


def run_triage(description: str) -> TriageResult:
    """
    Classify an IT support ticket.

    Retries temporary errors once.
    Stops immediately on quota errors.
    Returns a fallback result if classification fails.
    """

    messages = [
        ("system", SYSTEM_PROMPT),
        ("human", f"Ticket:\n{description}")
    ]

    last_error = "unknown error"

    for attempt in range(1, MAX_ATTEMPTS + 1):

        try:
            result = _get_chain().invoke(messages)

            if isinstance(result, dict):
                result = TriageResult(**result)

            if result is None:
                raise ValueError(
                    "Model returned no structured output"
                )

            return result

        except Exception as e:

            last_error = f"{type(e).__name__}: {e}"

            log.warning(
                "Triage attempt %d failed: %s",
                attempt,
                last_error[:200]
            )

            if _is_quota_error(e):
                log.error("LLM quota exhausted. Stopping retries.")
                break

            if attempt < MAX_ATTEMPTS:
                time.sleep(2)

    return fallback_result(last_error[:120])
