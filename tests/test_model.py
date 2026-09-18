"""Tests for tm1.run.model's own logic.

Not the step orchestration loop itself, which needs a real project to
exercise, but the small pieces around it.
"""

import pytest

from tm1.run import model as run_model


def test_notify_start_names_the_resume_step_not_the_full_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What changed is where a resume continues, not the full plan.

    Steps/sample/iteration detail describes a fresh run; a resume already ran
    the plan once.
    """
    sent = []
    monkeypatch.setattr(run_model, "notify", lambda msg, **_: sent.append(msg))

    run_model._notify_start(
        "proj:A_001", ["copy_inputs", "simulate_ctramp"], {}, 3,
        {"resume_at": "2:assignment"},
    )

    assert sent == [":rabbit2: Resuming proj:A_001 at 2:assignment"]


def test_notify_start_reports_the_full_plan_when_not_resuming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ordinary case is unchanged: steps, sample rate and iteration count."""
    sent = []
    monkeypatch.setattr(run_model, "notify", lambda msg, **_: sent.append(msg))

    run_model._notify_start(
        "proj:A_001", ["copy_inputs", "simulate_ctramp"],
        {("simulate_ctramp", 1): {"sample_rate": 0.5, "threads": 24}}, 3, {},
    )

    assert "steps: copy_inputs, simulate_ctramp" in sent[0]
    assert "iterations: 3" in sent[0]


def test_report_step_warns_but_does_not_look_like_success_when_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """continue_on_error (src/tm1/steps/external.py) returns "failed", not None."""
    sent = []
    monkeypatch.setattr(run_model, "notify", lambda msg, **_: sent.append(msg))

    run_model._report_step("proj:A_001", "npa_metrics_goal_3", "failed", 1.0)

    assert "failed" in sent[0]
