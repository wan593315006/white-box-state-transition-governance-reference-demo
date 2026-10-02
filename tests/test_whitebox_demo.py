import unittest
from dataclasses import replace

from wbstg import AgentGateway, CandidateTransition, Decision, Evidence, GovernanceKernel, Observation, PolicySnapshot, ReplayVerifier, StateSnapshot
from wbstg.ablation import ReducedSemanticBaseline


def state():
    return StateSnapshot("object-1", 7, "draft")


def policy(version="1.0.0"):
    return PolicySnapshot("review-policy", version, ("reviewed",), ("agent-1",))


def candidate(**changes):
    value = CandidateTransition(
        "c-1", "object-1", 7, state().node()["fingerprint"], "reviewed", "agent-1", "id-1",
    )
    return replace(value, **changes)


def evidence(**changes):
    value = Evidence("e-1", "object-1", 7, "evidence-content-sha")
    return replace(value, **changes)


class WhiteBoxStateTransitionGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.kernel = GovernanceKernel(state(), policy())
        self.agent = AgentGateway(self.kernel)

    def test_allow_applied_emits_complete_inspectable_lineage(self):
        result = self.agent.submit_candidate(candidate(), evidence())
        self.assertEqual((Decision.ALLOW.value, Observation.APPLIED.value), (result.decision, result.observation))
        self.assertEqual(1, self.kernel.simulated_effect_count)
        self.assertEqual(8, self.kernel.current_state.version)
        self.assertTrue(result.record_fingerprint)
        self.assertEqual("WBSTG-LINEAGE-1", result.schema_version)
        self.assertTrue(all(node is not None for node in (result.candidate, result.state_before, result.evidence, result.policy, result.state_after)))

    def test_invalid_principal_denies_without_effect(self):
        result = self.agent.submit_candidate(candidate(principal_id="untrusted"), evidence())
        self.assertEqual((Decision.DENY.value, "PRINCIPAL_NOT_AUTHORIZED_BY_POLICY", 0), (result.decision, result.reason_code, self.kernel.simulated_effect_count))

    def test_missing_or_refreshable_evidence_defers_without_effect(self):
        missing = self.agent.submit_candidate(candidate(), None)
        refresh = self.agent.submit_candidate(candidate(candidate_id="c-2", idempotency_key="id-2"), evidence(status="EXPIRED", refreshable=True))
        self.assertEqual(Decision.DEFER.value, missing.decision)
        self.assertEqual(Decision.DEFER.value, refresh.decision)
        self.assertEqual(0, self.kernel.simulated_effect_count)

    def test_high_risk_escalates_without_effect(self):
        result = self.agent.submit_candidate(candidate(risk="HIGH"), evidence())
        self.assertEqual((Decision.ESCALATE.value, Observation.NOT_RUN.value, 0), (result.decision, result.observation, self.kernel.simulated_effect_count))

    def test_allow_does_not_claim_success_when_observation_fails_or_unknown(self):
        failed = self.agent.submit_candidate(candidate(simulated_executor_outcome="FAILED"), evidence())
        unknown_kernel = GovernanceKernel(state(), policy())
        unknown = AgentGateway(unknown_kernel).submit_candidate(candidate(simulated_executor_outcome="UNKNOWN"), evidence())
        self.assertEqual((Decision.ALLOW.value, Observation.FAILED.value, 7), (failed.decision, failed.observation, self.kernel.current_state.version))
        self.assertEqual((Decision.ALLOW.value, Observation.UNKNOWN.value, 7), (unknown.decision, unknown.observation, unknown_kernel.current_state.version))

    def test_replay_verifies_original_lineage_without_second_effect(self):
        original_state = state()
        result = self.agent.submit_candidate(candidate(), evidence())
        verified, reason = ReplayVerifier.verify(result, candidate(), original_state, evidence(), policy())
        replay = self.agent.submit_candidate(candidate(), evidence())
        self.assertEqual((True, "REPLAY_VERIFIED_WITHOUT_EXECUTION", 1), (verified, reason, self.kernel.simulated_effect_count))
        self.assertTrue(replay.replayed)

        conflicts = {
            "candidate": candidate(target_state="other"),
            "evidence": candidate(),
            "original_state": candidate(
                base_state_version=8,
                base_state_fingerprint=StateSnapshot("object-1", 8, "reviewed").node()["fingerprint"],
            ),
        }
        for changed_input, changed_candidate in conflicts.items():
            with self.subTest(changed_input=changed_input):
                changed_evidence = evidence(content_hash="changed-evidence-sha") if changed_input == "evidence" else evidence()
                conflict = self.agent.submit_candidate(changed_candidate, changed_evidence)
                self.assertEqual(
                    (Decision.DENY.value, "IDEMPOTENCY_BOUND_INPUT_CONFLICT", Observation.NOT_RUN.value, 1),
                    (conflict.decision, conflict.reason_code, conflict.observation, self.kernel.simulated_effect_count),
                )

        with self.subTest(changed_input="policy"):
            self.kernel._policy = policy("2.0.0")
            conflict = self.agent.submit_candidate(candidate(), evidence())
            self.assertEqual(
                (Decision.DENY.value, "IDEMPOTENCY_BOUND_INPUT_CONFLICT", Observation.NOT_RUN.value, 1),
                (conflict.decision, conflict.reason_code, conflict.observation, self.kernel.simulated_effect_count),
            )

    def test_direct_tool_request_is_blocked_and_audited(self):
        result = self.agent.request_direct_tool_call("agent-1", "write-record")
        self.assertEqual((Decision.DENY.value, "DIRECT_TOOL_ACCESS_NOT_EXPOSED", Observation.NOT_RUN.value), (result.decision, result.reason_code, result.observation))
        self.assertEqual("BYPASS_BLOCKED", self.kernel.audit_events[-1]["event"])

    def test_evidence_binding_mismatch_denies(self):
        result = self.agent.submit_candidate(candidate(), evidence(object_id="other-object"))
        self.assertEqual("EVIDENCE_BINDING_MISMATCH", result.reason_code)

    def test_policy_snapshot_change_invalidates_replay(self):
        result = self.agent.submit_candidate(candidate(), evidence())
        verified, reason = ReplayVerifier.verify(result, candidate(), state(), evidence(), policy("2.0.0"))
        self.assertEqual((False, "POLICY_SNAPSHOT_FINGERPRINT_MISMATCH"), (verified, reason))

    def test_tampered_record_fails_replay_verification(self):
        result = self.agent.submit_candidate(candidate(), evidence())
        tampered = replace(result, reason_code="TAMPERED")
        verified, reason = ReplayVerifier.verify(tampered, candidate(), state(), evidence(), policy())
        self.assertEqual((False, "RECORD_FINGERPRINT_MISMATCH"), (verified, reason))

    def test_ablation_without_evidence_context_binding_accepts_wrong_evidence(self):
        baseline = ReducedSemanticBaseline(state())
        outcome = baseline.accepts_evidence_without_context_binding(candidate(), evidence(object_id="other-object", state_version=999))
        self.assertEqual("ACCEPTED_WITHOUT_OBJECT_OR_VERSION_CHECK", outcome.reduced_baseline_behavior)

    def test_ablation_without_state_version_binding_accepts_stale_transition(self):
        baseline = ReducedSemanticBaseline(state())
        outcome = baseline.accepts_transition_without_current_state_binding(candidate(base_state_version=1))
        self.assertEqual("ACCEPTED_WITHOUT_CURRENT_STATE_VERSION_CHECK", outcome.reduced_baseline_behavior)

    def test_ablation_without_observation_binding_advances_after_failure(self):
        baseline = ReducedSemanticBaseline(state())
        outcome = baseline.advances_state_without_observation_binding(candidate(), Observation.FAILED)
        self.assertEqual("STATE_ADVANCED_WITHOUT_CHECKING_FAILED", outcome.reduced_baseline_behavior)
        self.assertEqual(8, baseline.current_state.version)

    def test_ablation_without_replay_binding_cannot_check_history(self):
        baseline = ReducedSemanticBaseline(state())
        outcome = baseline.replay_without_bound_lineage()
        self.assertEqual("HISTORICAL_REPLAY_NOT_CHECKABLE_WITHOUT_BOUND_LINEAGE", outcome.reduced_baseline_behavior)


if __name__ == "__main__":
    unittest.main()
