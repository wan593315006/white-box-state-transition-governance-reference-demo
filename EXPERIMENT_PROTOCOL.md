# Fixed Case Experiment Protocol

## Purpose

This protocol evaluates the deterministic reference model, not a production
agent, an LLM chain of thought, or a real external tool. Each case begins with a
new in-memory kernel and a fixed state, candidate, evidence value, and policy
snapshot.

## Cases and expected observable results

| Case | Changed condition | Expected decision | Expected observation | Simulated effect |
|---|---|---|---|---|
| C1 | valid lineage | ALLOW | APPLIED | one |
| C2 | unauthorized principal | DENY | NOT_RUN | zero |
| C3 | missing evidence | DEFER | NOT_RUN | zero |
| C4 | high risk | ESCALATE | NOT_RUN | zero |
| C5 | executor failure after ALLOW | ALLOW | FAILED | zero state advance |
| C6 | exact replay | original decision retained | original observation retained | no second effect |
| I1 | direct tool request | DENY | NOT_RUN | zero |

## Recorded fields

For each case, the runner emits the complete `LineageRecord`, including
fingerprints for the candidate, state snapshot, evidence, policy snapshot, and
whole record. It also emits the effect count and post-case state.

An idempotency replay is valid only when the candidate, evidence, policy, and
original state snapshot all match the first submission. A changed bound input is
rejected with `IDEMPOTENCY_BOUND_INPUT_CONFLICT`; it is not treated as a replay.

## Metrics and interpretation

- **Expected-decision agreement:** fraction of cases whose decision equals the
  declared expected decision.
- **Expected-observation agreement:** fraction whose observation equals the
  declared expected observation.
- **Replay verification rate:** fraction of declared replay checks whose record
  verifies with the original nodes and no second effect.

For this fixed deterministic suite, a 100 percent score means only that the
reference implementation agrees with its declared cases. It is not a safety
rate, performance benchmark, external-policy comparison, or production claim.

## Semantic ablation

`tools/run_semantic_ablation.py` runs a deliberately reduced in-memory
baseline. It removes evidence-context binding, current-state-version binding,
observation-aware state advancement, and bound-lineage replay verification.
It is not a comparison with an external policy product. The four cases record
which reference-model property is no longer checked when the corresponding
binding is omitted. No network, filesystem, shell, provider, or external tool
is invoked.

## Reproduction

```text
set PYTHONPATH=src
python tools/run_reference_cases.py
python tools/run_semantic_ablation.py
python -m unittest discover -s tests -v
```
