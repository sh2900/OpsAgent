
import logging

from agents import tools
from backend.models import DiagnosisResult, ResolutionResult


log = logging.getLogger(__name__)


# ---------- Action execution ----------

def _execute_action(action: str, username: str) -> dict:
    """Execute one approved corrective action."""

    if action == "reset_vpn":
        return tools.reset_vpn()

    if action == "unlock_account":
        return tools.unlock_account(username)

    if action == "reset_password":
        return tools.reset_password(username)

    if action == "cleanup_disk":
        return tools.cleanup_disk()

    raise ValueError(f"Unsupported action: {action}")


# ---------- Safety validation ----------

def _action_is_applicable(
    diagnosis: DiagnosisResult,
    action: str
) -> bool:
    """Check whether the diagnostic evidence supports the action."""

    details = diagnosis.details
    status = diagnosis.service_status

    if action == "reset_vpn":
        return (
            diagnosis.service == "VPN"
            and status != "up"
            and details.get("fixable") is True
        )

    if action == "unlock_account":
        return (
            diagnosis.service == "Account"
            and status == "locked"
            and details.get("fixable") is True
        )

    if action == "reset_password":
        return (
            diagnosis.service == "Account"
            and status == "password_expired"
            and details.get("fixable") is True
        )

    if action == "cleanup_disk":
        return (
            diagnosis.service == "Disk"
            and status in {"critical", "warning"}
        )

    return False


# ---------- Post-fix verification ----------

def _verify_fix(service: str, username: str) -> bool:
    """Check whether the service has reached its expected state."""

    if service == "VPN":
        result = tools.check_vpn()
        return result.get("status") == "up"

    if service == "Account":
        result = tools.check_account(username)
        return result.get("status") == "active"

    if service == "Disk":
        result = tools.check_disk()
        return result.get("level") in {"warning", "ok"}

    return False


# ---------- Main entry point ----------

def run_resolution(
    diagnosis: DiagnosisResult,
    username: str
) -> ResolutionResult:
    """
    Execute the Diagnostic Agent's recommendation,
    verify the result and escalate when necessary.
    Never allows unsupported actions to execute.
    """

    service = diagnosis.service
    action = diagnosis.recommended_action

    # 1. Check whether the service is supported.
    if service not in tools.ALLOWED_ACTIONS:
        return ResolutionResult(
            escalated=True,
            escalation_reason="Service is outside the supported resolution scope.",
            message="This issue requires human support."
        )

    # 2. No action was recommended.
    if action is None:
        if diagnosis.service_status in {
            "up", "active", "ok"
        }:
            return ResolutionResult(
                message=(
                    "No corrective action required. "
                    "The service appears healthy."
                )
            )

        reason = diagnosis.probable_cause

        return ResolutionResult(
            escalated=True,
            escalation_reason=reason,
            message=(
                "No automatic fix is available. "
                "The issue requires human intervention."
            )
        )

    # 3. Validate the action against the service's allowlist.
    if action not in tools.ALLOWED_ACTIONS[service]:
        return ResolutionResult(
            escalated=True,
            escalation_reason=(
                f"Action '{action}' is not approved for service '{service}'."
            ),
            message="The proposed action was rejected for safety."
        )

    # 4. Validate whether the action is supported by diagnostic evidence.
    if not _action_is_applicable(diagnosis, action):
        return ResolutionResult(
            escalated=True,
            escalation_reason=(
                "The recommended action is not supported "
                "by the diagnostic status details."
            ),
            message=(
                "Automatic resolution was stopped. "
                "Human intervention is required."
            )
        )

    # 5. Execute the corrective action.
    try:
        action_result = _execute_action(action, username)

        operation_success = action_result.get("success") is True
        action_message = action_result.get(
            "message", "No action message returned."
        )

        # 6. Verify the service's actual status.
        verified = _verify_fix(service, username)

        fix_succeeded = operation_success and verified

        if fix_succeeded:
            return ResolutionResult(
                action_taken=action,
                fix_succeeded=True,
                verified=True,
                escalated=False,
                message=(
                    f"{action_message}. "
                    "The service status was verified successfully."
                )
            )

        # 7. The action failed or the post-fix check did not pass.
        reason = (
            action_message
            if not operation_success
            else "The corrective action ran, but verification failed."
        )

        return ResolutionResult(
            action_taken=action,
            fix_succeeded=False,
            verified=verified,
            escalated=True,
            escalation_reason=reason,
            message=(
                "Automatic resolution was unsuccessful. "
                "The issue has been escalated for human intervention."
            )
        )

    except tools.BackendUnreachable as e:
        log.error("Resolution backend unavailable: %s", e)

        return ResolutionResult(
            action_taken=action,
            escalated=True,
            escalation_reason=str(e),
            message=(
                "Could not complete or verify the corrective action "
                "because the IT backend is unavailable."
            )
        )

    except Exception as e:
        log.exception("Unexpected error during resolution")

        return ResolutionResult(
            action_taken=action,
            escalated=True,
            escalation_reason=str(e),
            message="An unexpected error occurred during resolution."
        )
