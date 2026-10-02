"""Deliberately reduced semantic baseline for the public reference experiment.

This module is an in-memory ablation fixture, not a policy engine and not an
external execution path.  It intentionally omits four lineage bindings so the
experiment can state, with executable evidence, which reference-model
properties are no longer checked.
"""

from dataclasses import dataclass
from typing import Optional

from .models import CandidateTransition, Evidence, Observation, StateSnapshot


@dataclass(frozen=True)
class AblationOutcome:
    property_name: str
    reference_property: str
    reduced_baseline_behavior: str


class ReducedSemanticBaseline:
    """A deliberately incomplete baseline with no external side effects."""

    def __init__(self, initial_state: StateSnapshot) -> None:
        self._state = initial_state
        self._simulated_effect_count = 0

    @property
    def current_state(self) -> StateSnapshot:
        return self._state

    @property
    def simulated_effect_count(self) -> int:
        return self._simulated_effect_count

    def accepts_evidence_without_context_binding(
        self, candidate: CandidateTransition, evidence: Optional[Evidence]
    ) -> AblationOutcome:
        # Intentionally retains only an evidence-present check.
        accepted = evidence is not None and evidence.status == "VALID"
        return AblationOutcome(
            "evidence_context_binding",
            "wrong-object or wrong-version evidence is rejected",
            "ACCEPTED_WITHOUT_OBJECT_OR_VERSION_CHECK" if accepted else "EVIDENCE_ABSENT",
        )

    def accepts_transition_without_current_state_binding(
        self, candidate: CandidateTransition
    ) -> AblationOutcome:
        # Intentionally does not compare candidate.base_state_version with state.
        return AblationOutcome(
            "state_version_binding",
            "stale candidate state version is escalated rather than executed",
            "ACCEPTED_WITHOUT_CURRENT_STATE_VERSION_CHECK",
        )

    def advances_state_without_observation_binding(
        self, candidate: CandidateTransition, observation: Observation
    ) -> AblationOutcome:
        # Intentionally advances after admission even if the observation failed.
        self._simulated_effect_count += 1
        self._state = StateSnapshot(candidate.object_id, self._state.version + 1, candidate.target_state)
        return AblationOutcome(
            "observation_aware_advancement",
            "only APPLIED advances simulated state",
            "STATE_ADVANCED_WITHOUT_CHECKING_" + observation.value,
        )

    def replay_without_bound_lineage(self) -> AblationOutcome:
        # A record/policy/evidence/candidate binding is deliberately absent.
        return AblationOutcome(
            "replay_binding",
            "candidate, state, evidence, policy, and record integrity are verified",
            "HISTORICAL_REPLAY_NOT_CHECKABLE_WITHOUT_BOUND_LINEAGE",
        )
