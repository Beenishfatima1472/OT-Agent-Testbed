"""
Step 3 isolation tests: verify the hash-chained log works correctly and,
critically, that tampering with an entry is detectable — before Step 4
(override gate) or Step 5 (agent harness) are built on top of it.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dsl.audit_log import AuditLog


def test_append_creates_linked_entries():
    log = AuditLog()
    e1 = log.append("agent reasoning 1", "set_battery_discharge_rate", {"rate_kw": 10}, "approved")
    e2 = log.append("agent reasoning 2", "shed_load", {"amount_kw": 20}, "approved")
    assert e2.prev_hash == e1.entry_hash
    assert e1.prev_hash == AuditLog.GENESIS_HASH


def test_chain_verifies_intact_by_default():
    log = AuditLog()
    log.append("r1", "shed_load", {"amount_kw": 20}, "approved")
    log.append("r2", "restore_load", {"amount_kw": 20}, "approved")
    log.append("r3", "shed_load", {"amount_kw": 999}, "rejected", ["out of range"])
    ok, bad_seq = log.verify_chain()
    assert ok is True
    assert bad_seq is None


def test_tampering_with_entry_content_is_detected():
    log = AuditLog()
    log.append("r1", "shed_load", {"amount_kw": 20}, "approved")
    log.append("r2", "restore_load", {"amount_kw": 20}, "approved")
    # simulate tampering: silently change a past disposition
    log._entries[0].disposition = "rejected"  # attacker edits history
    ok, bad_seq = log.verify_chain()
    assert ok is False
    assert bad_seq == 0


def test_tampering_with_prev_hash_link_is_detected():
    log = AuditLog()
    log.append("r1", "shed_load", {"amount_kw": 20}, "approved")
    log.append("r2", "restore_load", {"amount_kw": 20}, "approved")
    log._entries[1].prev_hash = "f" * 64  # attacker breaks the link
    ok, bad_seq = log.verify_chain()
    assert ok is False
    assert bad_seq == 1


def test_dispositions_reconstructable_from_log_alone():
    log = AuditLog()
    log.append("r1", "shed_load", {"amount_kw": 20}, "approved")
    log.append("r2", "set_battery_discharge_rate", {"rate_kw": 999}, "rejected", ["out of range"])
    log.append("r3", "shed_load", {"amount_kw": 999}, "needs_reprompt", ["out of range"])
    dispositions = log.reconstruct_dispositions()
    assert dispositions == {0: "approved", 1: "rejected", 2: "needs_reprompt"}


def test_override_and_timeout_dispositions_supported():
    log = AuditLog()
    log.append("r1", "set_battery_discharge_rate", {"rate_kw": 45}, "overridden_approved", operator_id="op-42")
    log.append("r2", "set_battery_discharge_rate", {"rate_kw": 48}, "timed_out_denied")
    dispositions = log.reconstruct_dispositions()
    assert dispositions[0] == "overridden_approved"
    assert dispositions[1] == "timed_out_denied"
    assert log.all_entries()[0].operator_id == "op-42"


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} -> {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
