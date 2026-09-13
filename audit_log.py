"""
Decision logging + tamper-evident audit trail (Components 2 and 4).

Every proposed action — approved, rejected, needing-reprompt, or later
overridden — produces one LogEntry, appended to a hash-chained store.
Each entry's hash covers its own content plus the previous entry's hash,
so any retroactive edit to an earlier entry breaks the chain from that
point forward and is detectable without a distributed ledger.

This is the log the evaluation harness (Step 6) reads to compute the
auditability success criterion: 100% of dispositions reconstructable
from the log alone, independent of agent self-report.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class LogEntry:
    seq: int
    timestamp: float
    agent_reasoning_trace: str
    action_type: str
    action_params: dict
    disposition: str          # "approved" | "rejected" | "needs_reprompt" | "overridden_approved" | "overridden_denied" | "timed_out_denied"
    policy_check_reasons: list[str]
    operator_id: Optional[str] = None
    prev_hash: str = ""
    entry_hash: str = field(default="", init=False)

    def compute_hash(self) -> str:
        payload = {
            "seq": self.seq,
            "timestamp": self.timestamp,
            "agent_reasoning_trace": self.agent_reasoning_trace,
            "action_type": self.action_type,
            "action_params": self.action_params,
            "disposition": self.disposition,
            "policy_check_reasons": self.policy_check_reasons,
            "operator_id": self.operator_id,
            "prev_hash": self.prev_hash,
        }
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def finalize(self) -> None:
        self.entry_hash = self.compute_hash()


class AuditLog:
    """Append-only, hash-chained log. No update/delete operations exposed."""

    GENESIS_HASH = "0" * 64

    def __init__(self):
        self._entries: list[LogEntry] = []

    def append(
        self,
        agent_reasoning_trace: str,
        action_type: str,
        action_params: dict,
        disposition: str,
        policy_check_reasons: Optional[list[str]] = None,
        operator_id: Optional[str] = None,
    ) -> LogEntry:
        prev_hash = self._entries[-1].entry_hash if self._entries else self.GENESIS_HASH
        entry = LogEntry(
            seq=len(self._entries),
            timestamp=time.time(),
            agent_reasoning_trace=agent_reasoning_trace,
            action_type=action_type,
            action_params=action_params,
            disposition=disposition,
            policy_check_reasons=policy_check_reasons or [],
            operator_id=operator_id,
            prev_hash=prev_hash,
        )
        entry.finalize()
        self._entries.append(entry)
        return entry

    def all_entries(self) -> list[LogEntry]:
        return list(self._entries)

    def verify_chain(self) -> tuple[bool, Optional[int]]:
        """
        Returns (True, None) if the chain is intact, or (False, seq) for
        the first entry whose stored hash no longer matches its recomputed
        hash or whose prev_hash link is broken.
        """
        expected_prev = self.GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != expected_prev:
                return False, entry.seq
            if entry.compute_hash() != entry.entry_hash:
                return False, entry.seq
            expected_prev = entry.entry_hash
        return True, None

    def reconstruct_dispositions(self) -> dict[int, str]:
        """
        Auditability criterion helper: rebuild seq -> disposition purely
        from the log, with no reference to agent state.
        """
        return {e.seq: e.disposition for e in self._entries}
