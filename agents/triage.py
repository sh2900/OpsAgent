
import logging
import time

from agents.llm import get_llm
from backend.models import TriageResult


log = logging.getLogger(__name__)

FALLBACK_MARKER = "Automatic triage failed"

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
IMPORTANT CATEGORY EVIDENCE RULES:

- Choose VPN only when the ticket explicitly mentions VPN,
  VPN client, VPN tunnel, certificate, gateway, or a
  specific remote-access connection problem.

- Do NOT assume an issue is VPN simply because the employee
  cannot access internal systems, company resources, or
  multiple work applications.

- Choose Account only when there is explicit evidence of
  a login, password, authentication, locked account,
  disabled account, or account permission issue.

- Password-related questions, password policy enquiries,
  password-change frequency questions and password-reset
  requests must also be classified as Account, even when
  the employee is not currently locked out or experiencing
  a login failure.

- Choose Disk only when there is explicit evidence of
  disk space, storage, a full drive, or inability to
  save files because of insufficient space.

- If the ticket describes a serious work disruption but
  does not identify a specific VPN, Account, or Disk issue,
  classify it as Other.

- Never invent a technical cause that the ticket does
  not mention.

- When a ticket explicitly identifies disk space as the
  reason another application or service cannot perform
  an operation, classify it as Disk.

- Classify based on the explicitly stated technical cause,
  not merely the application affected by that cause.

- For example, "Disk full error stopped my VPN software
  from updating" must be classified as Disk, not VPN or Other.

- Use Other only when the ticket does not provide enough
  evidence to identify VPN, Account, or Disk as the issue.

- VPN access requests, VPN setup questions, VPN configuration
  requests and requests to use VPN on personal devices must
  be classified as VPN, even when no connection failure
  is currently reported.

URGENCY (choose exactly one):

- High: The employee explicitly cannot perform essential work
  because a required service or account is completely unavailable;
  cannot save essential work files; multiple employees are affected;
  or an imminent hard deadline is threatened.

- Medium: The employee can still perform some work, but a
  particular application, feature, task or workflow is blocked,
  unreliable, slow or interrupted.

- Low: A general question, routine request, minor inconvenience,
  or warning with no demonstrated impact on current work.

IMPORTANT URGENCY DECISION RULES:

1. Do not assume that an employee cannot work simply because
   one application or feature is unavailable.

2. Do not assume that low disk space means the employee cannot
   save files. Only classify it as High when the ticket explicitly
   says essential files cannot be saved or work is completely blocked.

3. An intermittent VPN connection or an application failure
   affecting one feature is normally Medium unless the ticket
   explicitly establishes a complete work blockage or imminent
   deadline.

3A. A statement that an employee cannot connect to the company
    VPN does not, by itself, establish that essential work is
    completely blocked. Unless the ticket explicitly establishes
    that essential work or required systems are inaccessible,
    multiple employees are affected, or an imminent deadline is
    threatened, classify the issue as Medium.

4. A failed software update does not automatically mean the
   currently installed software or service is unavailable.

5. When the employee can continue performing other work,
   prefer Medium over High.

6. Never invent consequences, deadlines or business impacts
   that are not stated in the ticket.

7. When the impact is unclear, use Medium and do not assume
   a critical outage.
8. Noticeable system performance degradation, such as a
   laptop becoming slow because disk usage is very high,
   should be Medium even when the employee can still work.

9. An inability to complete one limited task, such as
   installing a software update, should normally be Medium
   unless it prevents essential work or creates an imminent
   deadline.

10. Low urgency is reserved for issues with no demonstrated
    current work disruption. Do not use Low merely because
    the system is still partially usable.

11. A low disk-space warning or a request to clean up storage
    must be Low when the ticket does not explicitly mention
    inability to save files, noticeable performance degradation,
    or another current work disruption.

12. Never infer that files cannot be saved merely because
    disk space is low. The ticket must explicitly state this.

13. A request for assistance is not automatically Medium.
    Classify based on the actual work impact described.
Give a one-sentence reasoning based only on the ticket.

14. If an employee explicitly cannot complete a specific
    technical task, such as installing a software update
    because disk space is insufficient, classify it as
    Medium unless essential work is completely blocked.

15. An explicit failure to complete a task is different
    from a low-space warning. A warning alone is Low,
    but an unsuccessful software installation is Medium.

16. Do not require inability to save essential files
    to classify a blocked individual task as Medium.
    That level of impact is relevant to High urgency.

"""

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
