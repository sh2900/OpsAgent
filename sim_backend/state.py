
"""In-memory state for the simulated IT environment."""

import copy

# Each scenario fully defines the state of the services.
SCENARIOS = {
    "healthy": {
        "vpn": {
            "status": "up",
            "cause": None,
            "fixable": True
        },
        "accounts": {
            "alice": {
                "status": "active",
                "failed_attempts": 0,
                "fixable": True
            },
            "bob": {
                "status": "active",
                "failed_attempts": 0,
                "fixable": True
            }
        },
        "disk": {
            "total_gb": 500,
            "used_gb": 200,
            "cleanup_frees_gb": 80
        }
    },

    "vpn_down": {
        "vpn": {
            "status": "down",
            "cause": "gateway_timeout",
            "fixable": True
        }
    },

    "vpn_cert_expired": {
        "vpn": {
            "status": "down",
            "cause": "expired_certificate",
            "fixable": False
        }
    },

    "account_locked": {
        "accounts": {
            "alice": {
                "status": "locked",
                "failed_attempts": 5,
                "fixable": True
            }
        }
    },

    "password_expired": {
        "accounts": {
            "bob": {
                "status": "password_expired",
                "failed_attempts": 0,
                "fixable": True
            }
        }
    },

    "account_disabled_by_hr": {
        "accounts": {
            "alice": {
                "status": "disabled",
                "failed_attempts": 0,
                "fixable": False
            }
        }
    },

    "disk_full": {
        "disk": {
            "total_gb": 500,
            "used_gb": 480,
            "cleanup_frees_gb": 120
        }
    },

    "disk_full_unfixable": {
        "disk": {
            "total_gb": 500,
            "used_gb": 490,
            "cleanup_frees_gb": 2
        }
    },

    "multi_failure": {
        "vpn": {
            "status": "degraded",
            "cause": "high_latency",
            "fixable": True
        },
        "accounts": {
            "alice": {
                "status": "locked",
                "failed_attempts": 5,
                "fixable": True
            }
        },
        "disk": {
            "total_gb": 500,
            "used_gb": 470,
            "cleanup_frees_gb": 100
        }
    }
}


# Current simulated environment
_state: dict = {}
_current_scenario = "healthy"


def load_scenario(name: str) -> None:
    """Start from healthy, then apply the selected scenario."""

    global _state, _current_scenario

    if name not in SCENARIOS:
        raise KeyError(name)

    _state = copy.deepcopy(SCENARIOS["healthy"])

    overlay = copy.deepcopy(SCENARIOS[name])

    for service, value in overlay.items():
        if service == "accounts":
            _state["accounts"].update(value)
        else:
            _state[service] = value

    _current_scenario = name


def get_state() -> dict:
    """Return the current simulated service state."""
    return _state


def current_scenario() -> str:
    """Return the currently selected scenario."""
    return _current_scenario


# Start with all services healthy.
load_scenario("healthy")
