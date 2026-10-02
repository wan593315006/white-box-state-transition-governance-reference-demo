"""Run the deterministic, side-effect-free semantic ablation experiment."""

import json

from wbstg import CandidateTransition, Evidence, Observation, StateSnapshot
from wbstg.ablation import ReducedSemanticBaseline


def main() -> None:
    state = StateSnapshot("object-1", 7, "draft")
    candidate = CandidateTransition(
        "c-1", "object-1", 7, state.node()["fingerprint"], "reviewed", "agent-1", "id-1",
    )
    wrong_evidence = Evidence("e-wrong", "other-object", 999, "content-sha")
    baseline = ReducedSemanticBaseline(state)
    outcomes = [
        baseline.accepts_evidence_without_context_binding(candidate, wrong_evidence),
        baseline.accepts_transition_without_current_state_binding(candidate),
        baseline.advances_state_without_observation_binding(candidate, Observation.FAILED),
        baseline.replay_without_bound_lineage(),
    ]
    print(json.dumps({
        "experiment": "semantic_ablation_v1",
        "external_side_effects": False,
        "outcome_count": len(outcomes),
        "outcomes": [outcome.__dict__ for outcome in outcomes],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
