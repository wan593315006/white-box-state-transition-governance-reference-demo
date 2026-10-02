# Architecture

The kernel owns the controlled executor. `AgentGateway` exposes only candidate
submission and a deliberately rejected direct-tool request. It does not expose
an executor handle.

```text
AgentGateway
  -> GovernanceKernel
       -> decision over Evidence, StateSnapshot, CandidateTransition, PolicySnapshot
       -> ControlledExecutor only when decision is ALLOW
       -> LineageRecord with fingerprints and observation
ReplayVerifier
  -> checks LineageRecord inputs and fingerprint without execution
```

The only execution adapter is `IN_MEMORY_CONTROLLED_EXECUTOR`. It records a
simulated state transition in memory when and only when observation is `APPLIED`.
