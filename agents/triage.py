
import logging
import time

from agents.llm import get_llm
from backend.models import TriageResult


log = logging.getLogger(__name__)


# Instructions given to Gemini
SYSTEM_PROMPT = """
You are the Ticket Triage Agent of an IT helpdesk system.

Read the employee's support ticket and decide two things.

CATEGORY (choose exactly one):

- VPN: remote access, VPN connection, tunnel, certificate
  or gateway problems.

- Account: login, password, locked or disabled account,
  access rights, authentication.

- Disk: low disk space, storage full, cannot save files
  because of space, slow due to full drive.

- Other: anything that is not clearly VPN, Account or Disk.
  Examples: printers, email, hardware, software installs,
  Wi-Fi, vague or unrelated requests.
  Use Other whenever you are unsure.

URGENCY (choose exactly one):

- High: the user cannot work at all, many people are
  affected, or there is a hard deadline.

- Medium: work is partly blocked or degraded, but a
  workaround exists.

- Low: minor inconvenience, a question, or a warning
  with no current impact.

Judge only from what the ticket says.
Do not invent details.

Give a one-sentence reasoning.
"""


MAX_ATTEMPTS = 2


def _get_chain():
    """Create a Gemini chain with structured output."""

    return get_llm().with_structured_output(TriageResult)


def fallback_result(reason: str) -> TriageResult:
    """Return a safe fallback when automatic triage fails."""

    return TriageResult(
        category="Other",
        urgency="Medium",
        reasoning=(
            f"Automatic triage failed ({reason}); "
            "routed for human review."
        )
    )


def run_triage(description: str) -> TriageResult:
    """
    Classify an IT support ticket.

    Retries once if Gemini fails.
    Returns a fallback result if both attempts fail.
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
                last_error
            )

            # Do not retry when the daily API quota is exhausted
            error_text = last_error.lower()

            quota_exceeded = any(
                term in error_text
                for term in (
                    "resource_exhausted",
                    "429",
                    "quota exceeded"
                )
            )

            if quota_exceeded:
                log.error("Gemini quota exhausted. Stopping retries.")
                break

            # Retry only temporary errors
            if attempt < MAX_ATTEMPTS:
                time.sleep(2)

    return fallback_result(last_error[:120])
