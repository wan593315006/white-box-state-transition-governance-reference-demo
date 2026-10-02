"""Emit the predeclared white-box reference cases as JSON; no file or network side effects."""

from dataclasses import asdict
import json

from wbstg import AgentGateway, CandidateTransition, Evidence, GovernanceKernel, PolicySnapshot, ReplayVerifier, StateSnapshot


def state():
    return StateSnapshot("object-1", 7, "draft")


def policy():
    return PolicySnapshot("review-policy", "1.0.0", ("reviewed",), ("agent-1",))


def candidate(case_id, **changes):
    value = {
        "candidate_id": case_id, "object_id": "object-1", "base_state_version": 7,
        "base_state_fingerprint": state().node()["fingerprint"],
        "target_state": "reviewed", "principal_id": "agent-1", "idempotency_key": case_id,
    }
    value.update(changes)
    return CandidateTransition(**value)


def evidence():
    return Evidence("evidence-1", "object-1", 7, "fixed-demo-evidence-content-hash")


def case_result(case_id, expected_decision, expected_observation, candidate_value=None, evidence_value=True):
    kernel = GovernanceKernel(state(), policy())
    agent = AgentGateway(kernel)
    result = agent.submit_candidate(candidate_value or candidate(case_id), evidence() if evidence_value else None)
    return {
        "case_id": case_id, "expected": {"decision": expected_decision, "observation": expected_observation},
        "actual": result.to_dict(), "simulated_effect_count": kernel.simulated_effect_count,
        "post_state": asdict(kernel.current_state),
    }


def main():
    results = [
        case_result("C1", "ALLOW", "APPLIED"),
        case_result("C2", "DENY", "NOT_RUN", candidate("C2", principal_id="untrusted")),
        case_result("C3", "DEFER", "NOT_RUN", candidate("C3"), False),
        case_result("C4", "ESCALATE", "NOT_RUN", candidate("C4", risk="HIGH")),
        case_result("C5", "ALLOW", "FAILED", candidate("C5", simulated_executor_outcome="FAILED")),
    ]

    replay_kernel = GovernanceKernel(state(), policy())
    replay_agent = AgentGateway(replay_kernel)
    original = replay_agent.submit_candidate(candidate("C6"), evidence())
    replay = replay_agent.submit_candidate(candidate("C6"), evidence())
    verified, reason = ReplayVerifier.verify(original, candidate("C6"), state(), evidence(), policy())
    results.append({
        "case_id": "C6", "expected": {"decision": "ALLOW", "observation": "APPLIED"},
        "actual": replay.to_dict(), "replay_verification": {"verified": verified, "reason": reason},
        "simulated_effect_count": replay_kernel.simulated_effect_count, "post_state": asdict(replay_kernel.current_state),
    })

    bypass_kernel = GovernanceKernel(state(), policy())
    bypass = AgentGateway(bypass_kernel).request_direct_tool_call("agent-1", "write-record")
    results.append({
        "case_id": "I1", "expected": {"decision": "DENY", "observation": "NOT_RUN"},
        "actual": bypass.to_dict(), "simulated_effect_count": bypass_kernel.simulated_effect_count,
        "post_state": asdict(bypass_kernel.current_state),
    })

    expected_decisions = sum(item["expected"]["decision"] == item["actual"]["decision"] for item in results)
    expected_observations = sum(item["expected"]["observation"] == item["actual"]["observation"] for item in results)
    print(json.dumps({
        "protocol": "WBSTG-FIXED-CASES-1", "case_count": len(results), "results": results,
        "summary": {
            "expected_decision_agreement": f"{expected_decisions}/{len(results)}",
            "expected_observation_agreement": f"{expected_observations}/{len(results)}",
            "replay_verification": "1/1" if verified and replay_kernel.simulated_effect_count == 1 else "0/1",
        },
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
