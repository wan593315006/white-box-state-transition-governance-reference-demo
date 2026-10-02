import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .kernel import AgentGateway, GovernanceKernel
from .models import CandidateTransition, Evidence, PolicySnapshot, StateSnapshot


def _load_case(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    state = StateSnapshot(**value["state_snapshot"])
    policy = PolicySnapshot(
        policy_id=value["policy_snapshot"]["policy_id"], version=value["policy_snapshot"]["version"],
        allowed_targets=tuple(value["policy_snapshot"]["allowed_targets"]),
        authorized_principals=tuple(value["policy_snapshot"]["authorized_principals"]),
        require_escalation_for_high_risk=value["policy_snapshot"].get("require_escalation_for_high_risk", True),
    )
    candidate = CandidateTransition(**value["candidate_transition"])
    evidence = Evidence(**value["evidence"]) if value.get("evidence") else None
    return state, policy, candidate, evidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one white-box governance reference case.")
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    state, policy, candidate, evidence = _load_case(args.case)
    result = AgentGateway(GovernanceKernel(state, policy)).submit_candidate(candidate, evidence)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
