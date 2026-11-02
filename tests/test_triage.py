
from agents import triage
from backend.models import TriageResult


# Fake Gemini response for testing
class FakeChain:

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1

        if self.error:
            raise self.error

        return self.result


# Test 1: Agent returns the expected model output
def test_returns_model_output(monkeypatch):

    expected = TriageResult(
        category="VPN",
        urgency="High",
        reasoning="Remote access is unavailable"
    )

    monkeypatch.setattr(
        triage,
        "_get_chain",
        lambda: FakeChain(result=expected)
    )

    result = triage.run_triage("VPN is down")

    assert result == expected


# Test 2: Dictionary output is converted into TriageResult
def test_dict_output_is_converted(monkeypatch):

    raw = {
        "category": "Disk",
        "urgency": "Low",
        "reasoning": "Storage warning"
    }

    monkeypatch.setattr(
        triage,
        "_get_chain",
        lambda: FakeChain(result=raw)
    )

    result = triage.run_triage("Disk is almost full")

    assert result.category == "Disk"
    assert isinstance(result, TriageResult)


# Test 3: Agent uses fallback after repeated failures
def test_falls_back_after_failures(monkeypatch):

    chain = FakeChain(
        error=RuntimeError("temporary service error")
    )

    monkeypatch.setattr(
        triage,
        "_get_chain",
        lambda: chain
    )

    # Avoid waiting during the retry
    monkeypatch.setattr(
        triage.time,
        "sleep",
        lambda s: None
    )

    result = triage.run_triage("Something is wrong")

    assert result.category == "Other"
    assert "temporary service error" in result.reasoning
    assert chain.calls == triage.MAX_ATTEMPTS


# Test 4: Agent uses fallback when model returns None
def test_none_output_falls_back(monkeypatch):

    monkeypatch.setattr(
        triage,
        "_get_chain",
        lambda: FakeChain(result=None)
    )

    monkeypatch.setattr(
        triage.time,
        "sleep",
        lambda s: None
    )

    result = triage.run_triage("Something is wrong")

    assert result.category == "Other"
