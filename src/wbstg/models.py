from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Dict, Optional, Tuple


def canonical_hash(value: Any) -> str:
    """Stable identity for public, serializable governance inputs and records."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(payload.encode("utf-8")).hexdigest()


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"
    ESCALATE = "ESCALATE"


class Observation(str, Enum):
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True)
class StateSnapshot:
    object_id: str
    version: int
    state: str

    def node(self) -> Dict[str, Any]:
        value = asdict(self)
        return {"value": value, "fingerprint": canonical_hash(value)}


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    object_id: str
    state_version: int
    content_hash: str
    status: str = "VALID"
    refreshable: bool = False

    def node(self) -> Dict[str, Any]:
        value = asdict(self)
        return {"value": value, "fingerprint": canonical_hash(value)}


@dataclass(frozen=True)
class PolicySnapshot:
    policy_id: str
    version: str
    allowed_targets: Tuple[str, ...]
    authorized_principals: Tuple[str, ...]
    require_escalation_for_high_risk: bool = True

    def node(self) -> Dict[str, Any]:
        value = asdict(self)
        return {"value": value, "fingerprint": canonical_hash(value)}


@dataclass(frozen=True)
class CandidateTransition:
    candidate_id: str
    object_id: str
    base_state_version: int
    base_state_fingerprint: str
    target_state: str
    principal_id: str
    idempotency_key: str
    risk: str = "LOW"
    simulated_executor_outcome: str = "APPLIED"

    def node(self) -> Dict[str, Any]:
        value = asdict(self)
        return {"value": value, "fingerprint": canonical_hash(value)}


@dataclass(frozen=True)
class LineageRecord:
    schema_version: str
    record_id: str
    candidate: Dict[str, Any]
    state_before: Dict[str, Any]
    evidence: Optional[Dict[str, Any]]
    policy: Dict[str, Any]
    decision: str
    reason_code: str
    controlled_execution: Dict[str, Any]
    observation: str
    state_after: Dict[str, Any]
    replayed: bool = False
    record_fingerprint: str = ""

    def without_record_fingerprint(self) -> Dict[str, Any]:
        value = asdict(self)
        value.pop("record_fingerprint", None)
        # Replay is delivery metadata, not part of the original signed lineage.
        value.pop("replayed", None)
        return value

    def with_fingerprint(self) -> "LineageRecord":
        return LineageRecord(**{**asdict(self), "record_fingerprint": canonical_hash(self.without_record_fingerprint())})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
