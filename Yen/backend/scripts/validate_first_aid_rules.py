"""Validate the structure and safety-review state of the first-aid rule seed."""
from __future__ import print_function

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "first_aid"

ALLOWED_DECISIONS = {"emergency", "non_emergency"}


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate(registry, rules):
    errors = []
    source_ids = {source.get("id") for source in registry.get("sources", [])}
    seen_rules = set()
    for rule in rules.get("rules", []):
        rule_id = rule.get("id")
        if not rule_id or rule_id in seen_rules:
            errors.append("Rule id missing or duplicated: {}".format(rule_id))
        seen_rules.add(rule_id)
        if rule.get("status") != "needs_clinician_review":
            errors.append("{} must remain needs_clinician_review in the seed".format(rule_id))
        if rule.get("decision") not in ALLOWED_DECISIONS:
            errors.append("{} has unsupported decision {}".format(rule_id, rule.get("decision")))
        if not rule.get("signals_any") and not rule.get("signals_all"):
            errors.append("{} needs at least one normalized signal".format(rule_id))
        if not rule.get("education_actions") or not rule.get("never_do"):
            errors.append("{} needs both education_actions and never_do safeguards".format(rule_id))
        review = rule.get("review") or {}
        if any(review.get(field) for field in ("clinical_approver", "reviewed_at", "expires_at")):
            errors.append("{} seed review fields must be blank until formally approved".format(rule_id))
        for evidence in rule.get("evidence", []):
            if evidence.get("source_id") not in source_ids:
                errors.append("{} cites missing source {}".format(rule_id, evidence.get("source_id")))
    if not rules.get("global_guards"):
        errors.append("Missing global safety guards")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate first-aid rule seed safety invariants")
    parser.add_argument("--registry", type=Path, default=DATA_DIR / "source_registry.json")
    parser.add_argument("--rules", type=Path, default=DATA_DIR / "rules.seed.json")
    args = parser.parse_args()
    errors = validate(read_json(args.registry), read_json(args.rules))
    if errors:
        for error in errors:
            print("ERROR: {}".format(error))
        return 1
    print("OK: first-aid registry and {} seed rules are structurally valid and pending clinical review.".format(len(read_json(args.rules).get("rules", []))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
