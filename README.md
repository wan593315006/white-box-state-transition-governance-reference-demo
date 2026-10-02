# White Box State Transition Governance Reference Demo

Public reference release: **v0.2.2**. See `CITATION.cff`, `LICENSE.md`,
`REPRODUCIBILITY.md`, and `RELEASE_MANIFEST.json` for release identity,
permitted use, reproduction, and integrity information.

This is a minimal, deterministic reference demonstration for candidate-first,
evidence-bound governance of a proposed state transition. It is independent of
Five Body and does not contain any Five Body source, method library, provider
configuration, secret, network client, shell adapter, or real tool executor.

## What is white box here

The demo does **not** claim access to an LLM's hidden reasoning. Its white-box
property is the inspectable governance lineage for one proposed external state
transition:

```text
Evidence -> State Snapshot -> Candidate Transition -> Policy Snapshot
-> Decision and Reason Code -> Controlled Execution -> Observation
-> Replayable Lineage Record
```

Every lineage node is serializable and fingerprinted. A record includes the
candidate, its required evidence, its state snapshot, policy snapshot, decision,
reason code, execution boundary, observed outcome, resulting state, and a record
fingerprint. Replay verification checks the original nodes without running the
executor again.

An idempotency key is not a reusable permission token. A replay is accepted only
when the candidate, evidence, policy, and original state snapshot remain exactly
bound to the first accepted submission. Any change to one of those inputs returns
`DENY / IDEMPOTENCY_BOUND_INPUT_CONFLICT` and does not invoke the executor.

## What it demonstrates

1. valid evidence, matching state/version and policy-authorized principal:
   `ALLOW -> APPLIED`;
2. unauthorized principal: `DENY`, no effect;
3. missing or refreshable evidence: `DEFER`, no effect;
4. high-risk candidate: `ESCALATE`, no effect;
5. an allowed simulated executor can still report `FAILED` or `UNKNOWN`; this
   does not advance state or claim success;
6. a lineage can be replay-verified without a second effect;
7. the public agent gateway rejects direct-tool requests and records the block.
8. a deliberately reduced semantic baseline shows which checks disappear when
   evidence-context, current-state-version, observation, or replay bindings are
   removed; it is not an external-product comparison.

## Explicit limits

- The controlled executor is in memory only. It has no network, file, shell,
  MCP, provider, database, or real external side effect.
- `ALLOW` means the candidate is eligible for the demo's controlled executor;
  it does not mean an external action succeeded.
- The gateway-level direct-tool invariant is not a claim of protection against
  hostile in-process Python code. A production deployment would require process
  and capability isolation.
- This demo does not implement method evolution, confidence scoring, hidden
  reasoning inspection, or Five Body runtime integration.

## Contact and collaboration

For research collaboration, evaluation, or commercial authorization enquiries,
contact **593315006@qq.com**. Commercial use is not granted by this repository
and requires prior written authorization from the Licensor.

After GitHub Discussions are enabled, use them for public technical questions.
Use Issues for reproducible defects in this reference demo. Do not post
credentials, confidential business information, or protected technical details
in public threads.

## Run

Python 3.9+ and the standard library are sufficient.

```text
python -m pip install .
python -m unittest discover -s tests -v
wbstg-demo examples/valid_transition.json
python tools/run_reference_cases.py
python tools/run_semantic_ablation.py
```

From a source checkout without installation:

```text
set PYTHONPATH=src
python -m unittest discover -s tests -v
python -m wbstg.cli examples/valid_transition.json
python tools/run_reference_cases.py
python tools/run_semantic_ablation.py
```

`EXPERIMENT_PROTOCOL.md` specifies the seven fixed cases, the bypass invariant,
the recorded fields, and the narrow interpretation of their metrics.
