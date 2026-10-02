from dataclasses import replace
from typing import Dict, List, Optional, Tuple

from .models import (
    CandidateTransition, Decision, Evidence, LineageRecord, Observation, PolicySnapshot,
    StateSnapshot, canonical_hash,
)


class ControlledExecutor:
    """In-memory stand-in. It has no network, shell, file, or provider integration."""

    def __init__(self) -> None:
        self._simulated_effects: List[str] = []

    @property
    def effect_count(self) -> int:
        return len(self._simulated_effects)

    def execute(self, candidate: CandidateTransition) -> Observation:
        outcome = candidate.simulated_executor_outcome.upper()
        if outcome == "FAILED":
            return Observation.FAILED
        if outcome == "UNKNOWN":
            return Observation.UNKNOWN
        self._simulated_effects.append(candidate.candidate_id)
        return Observation.APPLIED


class GovernanceKernel:
    """Candidate-first governance that emits a complete inspectable lineage record."""

    def __init__(self, initial_state: StateSnapshot, policy: PolicySnapshot) -> None:
        self._state = initial_state
        self._policy = policy
        self._executor = ControlledExecutor()
        self._records_by_key: Dict[str, LineageRecord] = {}
        self.audit_events: List[Dict[str, str]] = []

    @property
    def current_state(self) -> StateSnapshot:
        return self._state

    @property
    def simulated_effect_count(self) -> int:
        return self._executor.effect_count

    def submit(self, candidate: CandidateTransition, evidence: Optional[Evidence]) -> LineageRecord:
        candidate_node = candidate.node()
        state_before = self._state
        prior = self._records_by_key.get(candidate.idempotency_key)
        if prior is not None:
            if not self._matches_original_submission(prior, candidate_node, evidence):
                return self._make_record(
                    candidate, evidence, state_before, Decision.DENY,
                    "IDEMPOTENCY_BOUND_INPUT_CONFLICT", Observation.NOT_RUN,
                )
            self.audit_events.append({"event": "REPLAY_REQUEST", "record_id": prior.record_id})
            return replace(prior, replayed=True)

        decision, reason = self._decide(candidate, evidence)
        observation = Observation.NOT_RUN
        if decision is Decision.ALLOW:
            observation = self._executor.execute(candidate)
            if observation is Observation.APPLIED:
                self._state = StateSnapshot(candidate.object_id, self._state.version + 1, candidate.target_state)

        record = self._make_record(candidate, evidence, state_before, decision, reason, observation)
        self._records_by_key[candidate.idempotency_key] = record
        self.audit_events.append({"event": "DECISION", "record_id": record.record_id, "decision": decision.value, "reason": reason})
        return record

    def _matches_original_submission(
        self, prior: LineageRecord, candidate_node: Dict[str, object], evidence: Optional[Evidence],
    ) -> bool:
        """Replay is valid only for the exact candidate, evidence, policy, and source state."""
        current_evidence = evidence.node() if evidence else None
        return (
            prior.candidate["fingerprint"] == candidate_node["fingerprint"]
            and prior.evidence == current_evidence
            and prior.policy["fingerprint"] == self._policy.node()["fingerprint"]
            and prior.state_before["fingerprint"] == candidate_node["value"]["base_state_fingerprint"]
        )

    def _decide(self, candidate: CandidateTransition, evidence: Optional[Evidence]) -> Tuple[Decision, str]:
        if candidate.principal_id not in self._policy.authorized_principals:
            return Decision.DENY, "PRINCIPAL_NOT_AUTHORIZED_BY_POLICY"
        if evidence is None:
            return Decision.DEFER, "EVIDENCE_MISSING"
        if evidence.status != "VALID":
            return (Decision.DEFER, "EVIDENCE_REFRESH_REQUIRED") if evidence.refreshable else (Decision.DENY, "EVIDENCE_INVALID")
        if evidence.object_id != candidate.object_id or evidence.state_version != candidate.base_state_version:
            return Decision.DENY, "EVIDENCE_BINDING_MISMATCH"
        if candidate.base_state_version != self._state.version or candidate.object_id != self._state.object_id:
            return Decision.ESCALATE, "CURRENT_STATE_VERSION_CONFLICT"
        if candidate.base_state_fingerprint != self._state.node()["fingerprint"]:
            return Decision.ESCALATE, "CURRENT_STATE_FINGERPRINT_CONFLICT"
        if candidate.target_state not in self._policy.allowed_targets:
            return Decision.DENY, "TARGET_STATE_NOT_ALLOWED_BY_POLICY"
        if self._policy.require_escalation_for_high_risk and candidate.risk.upper() == "HIGH":
            return Decision.ESCALATE, "HIGH_RISK_REQUIRES_HUMAN_REVIEW"
        return Decision.ALLOW, "CANDIDATE_TRANSITION_QUALIFIED"

    def _make_record(
        self, candidate: CandidateTransition, evidence: Optional[Evidence], state_before: StateSnapshot,
        decision: Decision, reason: str, observation: Observation,
    ) -> LineageRecord:
        record_id = "lin-" + canonical_hash({"candidate": candidate.node()["fingerprint"], "policy": self._policy.node()["fingerprint"]})[:16]
        controlled_execution = {
            "adapter": "IN_MEMORY_CONTROLLED_EXECUTOR",
            "external_side_effects": False,
            "invoked": decision is Decision.ALLOW,
            "execution_authorized": decision is Decision.ALLOW,
        }
        return LineageRecord(
            schema_version="WBSTG-LINEAGE-1", record_id=record_id, candidate=candidate.node(),
            state_before=state_before.node(), evidence=evidence.node() if evidence else None,
            policy=self._policy.node(), decision=decision.value, reason_code=reason,
            controlled_execution=controlled_execution, observation=observation.value,
            state_after=self._state.node(),
        ).with_fingerprint()


class AgentGateway:
    """The sole public agent surface. It deliberately exposes no executor or tool handle."""

    def __init__(self, kernel: GovernanceKernel) -> None:
        self._kernel = kernel

    def submit_candidate(self, candidate: CandidateTransition, evidence: Optional[Evidence]) -> LineageRecord:
        return self._kernel.submit(candidate, evidence)

    def request_direct_tool_call(self, principal_id: str, requested_action: str) -> LineageRecord:
        self._kernel.audit_events.append({"event": "BYPASS_BLOCKED", "principal_id": principal_id, "requested_action": requested_action})
        candidate = CandidateTransition(
            candidate_id="bypass:" + principal_id, object_id=self._kernel.current_state.object_id,
            base_state_version=self._kernel.current_state.version,
            base_state_fingerprint=self._kernel.current_state.node()["fingerprint"],
            target_state="NONE", principal_id=principal_id,
            idempotency_key="bypass:" + canonical_hash({"principal_id": principal_id, "requested_action": requested_action}),
        )
        return self._kernel._make_record(
            candidate, None, self._kernel.current_state, Decision.DENY,
            "DIRECT_TOOL_ACCESS_NOT_EXPOSED", Observation.NOT_RUN,
        )


class ReplayVerifier:
    """Verifies supplied white-box nodes against a stored record without invoking execution."""

    @staticmethod
    def verify(record: LineageRecord, candidate: CandidateTransition, state_before: StateSnapshot,
               evidence: Optional[Evidence], policy: PolicySnapshot) -> Tuple[bool, str]:
        if record.record_fingerprint != canonical_hash(record.without_record_fingerprint()):
            return False, "RECORD_FINGERPRINT_MISMATCH"
        if record.candidate["fingerprint"] != candidate.node()["fingerprint"]:
            return False, "CANDIDATE_FINGERPRINT_MISMATCH"
        if record.state_before["fingerprint"] != state_before.node()["fingerprint"]:
            return False, "STATE_SNAPSHOT_FINGERPRINT_MISMATCH"
        expected_evidence = evidence.node() if evidence else None
        if record.evidence != expected_evidence:
            return False, "EVIDENCE_FINGERPRINT_MISMATCH"
        if record.policy["fingerprint"] != policy.node()["fingerprint"]:
            return False, "POLICY_SNAPSHOT_FINGERPRINT_MISMATCH"
        return True, "REPLAY_VERIFIED_WITHOUT_EXECUTION"
