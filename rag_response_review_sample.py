"""Synthetic metadata checks, not semantic verification or access enforcement."""
from __future__ import annotations

import json

CATALOG = {
    "S1": {"version": "v2", "scope": "public"},
    "S2": {"version": "v3", "scope": "team"},
    "S3": {"version": "v1", "scope": "public"},
}


def response(source_ids=None, versions=None, evidence=True, mode="answer", **extra):
    """Build synthetic fixtures; no documents or model calls are involved."""
    return {"answer_mode": mode, "evidence_present": evidence,
            "source_ids": ["S1"] if source_ids is None else source_ids,
            "source_versions": {"S1": "v2"} if versions is None else versions,
            **extra}


SYNTHETIC_CASES = [
    {"case_id": "C1-valid", "response": response()},
    {"case_id": "C2-unknown-source", "response": response(["S9"], {"S9": "v1"})},
    {"case_id": "C3-correct-abstention", "response": response([], {}, False, "abstain")},
    {"case_id": "C4-permission-mismatch", "response": response(["S2"], {"S2": "v3"})},
    {"case_id": "C5-version-mismatch", "response": response(["S1"], {"S1": "v1"})},
    {"case_id": "C6-malformed-list", "response": response("S1")},
    {"case_id": "C7-stale-marker", "response": response(stale_source_ids=["S1"])},
    {"case_id": "C8-unsupported-answer", "response": response([], {}, False)},
]


def _string_list(value, name, issues):
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        issues.append(name + "_must_be_string_list")
        return []
    return value


def review_response(case, granted_scopes=("public",)):
    """Scopes come from the caller, not a response's self-declared permission."""
    if not isinstance(case, dict) or not isinstance(case.get("case_id"), str):
        raise ValueError("case must have a string case_id")
    if (isinstance(granted_scopes, str) or
            not isinstance(granted_scopes, (list, tuple, set, frozenset)) or
            any(not isinstance(x, str) for x in granted_scopes)):
        raise ValueError("granted_scopes must be a collection of strings")
    data, issues = case.get("response"), []
    if not isinstance(data, dict):
        return {"case_id": case["case_id"], "decision": "flag",
                "issues": ["response_must_be_mapping"]}
    ids = _string_list(data.get("source_ids"), "source_ids", issues)
    stale = _string_list(data.get("stale_source_ids", []), "stale_source_ids", issues)
    mode, evidence = data.get("answer_mode"), data.get("evidence_present")
    if mode not in ("answer", "abstain"):
        issues.append("invalid_answer_mode")
    if not isinstance(evidence, bool):
        issues.append("evidence_present_must_be_boolean")
    if evidence is False and mode != "abstain":
        issues.append("no_evidence_requires_abstain")
    if evidence is False and ids:
        issues.append("citations_conflict_with_no_evidence")
    if evidence is True and not ids:
        issues.append("evidence_requires_source_ids")
    versions = data.get("source_versions")
    if not isinstance(versions, dict):
        issues.append("source_versions_must_be_mapping")
        versions = {}
    for source_id in ids:
        entry = CATALOG.get(source_id)
        if entry is None:
            issues.append("unknown_source:" + source_id)
            continue
        if entry["scope"] not in granted_scopes:
            issues.append("permission_mismatch:" + source_id)
        if versions.get(source_id) != entry["version"]:
            issues.append("version_mismatch:" + source_id)
    issues.extend("stale_marker:" + source_id for source_id in stale)
    decision = "flag" if issues else ("abstain" if mode == "abstain" else "pass")
    return {"case_id": case["case_id"], "decision": decision,
            "issues": sorted(set(issues))}


def run_all():
    return [review_response(case) for case in SYNTHETIC_CASES]


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2, sort_keys=True))
