"""Local recipe retrieval and evidence-gated admission. No model or network calls."""
import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "references" / "recipes"
INDEX = CARDS / "index.json"
STATUSES = {"candidate", "user-style-approved", "reviewed-local", "cross-product-validated", "deprecated", "rejected", "reference-library"}
REQUIRED_PASS = {"product_identity", "copy_and_claims", "style_match", "product_priority", "purpose_expression", "material_scale"}
OPTIONAL_CHECKS = {"contact_and_operation", "spatial_type", "effects", "set_consistency"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verified_file(ref, base):
    require(isinstance(ref, dict), "File reference must be an object")
    name, expected = ref.get("file"), ref.get("sha256")
    require(isinstance(name, str) and name, "Missing file path")
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected), f"Invalid SHA-256: {name}")
    path = Path(name)
    path = path.resolve() if path.is_absolute() else (base / path).resolve()
    require(path.is_file(), f"Missing evidence file: {path}")
    require(digest(path) == expected, f"Evidence changed: {path}")
    return path


def validate_card(card, check_assets=True):
    require(card.get("schema_version") == 1, "Unsupported card schema")
    require(re.fullmatch(r"[a-z][a-z0-9-]{0,63}", card.get("id", "")), "Invalid recipe id")
    require(type(card.get("version")) is int and card["version"] > 0, "Version must be a positive integer")
    require(card.get("status") in STATUSES, "Invalid recipe status")
    for key in ("title", "transfer", "forbidden_inheritance", "failure_notes", "assets"):
        require(card.get(key), f"Missing card field: {key}")
    profile = card.get("profile", {})
    for key in ("morphologies", "purposes", "styles", "routes", "categories"):
        require(isinstance(profile.get(key), list) and profile[key] and all(isinstance(v, str) and v for v in profile[key]), f"Invalid profile: {key}")
    assets = card["assets"]
    require(all(isinstance(a, dict) and a.get("id") for a in assets), "Asset ids required")
    asset_ids = {a["id"] for a in assets}
    require(len(asset_ids) == len(assets), "Duplicate asset id")
    patterns = card.get("purpose_patterns", [])
    require({p.get("purpose") for p in patterns} == set(profile["purposes"]) and len(patterns) == len(profile["purposes"]), "Each purpose needs exactly one pattern")
    for p in patterns:
        require(p.get("actions") and p.get("intent") and p.get("prompt_template"), "Incomplete purpose pattern")
        require(p.get("asset_ids") and set(p["asset_ids"]) <= asset_ids, "Pattern references missing assets")
    if check_assets:
        for a in assets:
            verified_file(a, ROOT)
    return card


def catalog():
    rows = []
    for path in sorted(CARDS.glob("*.v*.json")):
        card = validate_card(read_json(path))
        rows.append((path, card))
    keys = [(c["id"], c["version"]) for _, c in rows]
    require(len(keys) == len(set(keys)), "Duplicate recipe version")
    return rows


def compact_index(rows):
    return {"schema_version": 1, "recipes": [{
        "id": c["id"], "version": c["version"], "title": c["title"], "status": c["status"],
        "file": p.relative_to(ROOT).as_posix(), "profile": c["profile"], "sha256": digest(p)
    } for p, c in rows]}


def find_recipes(args):
    # Read only a compact index, then the strongest cards. Older versions stay available
    # but cannot silently defeat a latest-version deprecation.
    idx = read_json(INDEX)
    latest = {}
    for item in idx["recipes"]:
        if item["id"] not in latest or item["version"] > latest[item["id"]]["version"]:
            latest[item["id"]] = item
    eligible = []
    for item in latest.values():
        p = item["profile"]
        if item["status"] in {"candidate", "deprecated", "rejected"}:
            continue
        if args.route not in p["routes"] or args.purpose not in p["purposes"] or args.morphology not in p["morphologies"]:
            continue
        card_path = verified_file({"file": item["file"], "sha256": item["sha256"]}, ROOT)
        card = read_json(card_path)
        pattern = next(x for x in card["purpose_patterns"] if x["purpose"] == args.purpose)
        action_match = bool(args.action and args.action in pattern["actions"])
        style_match = bool(args.style and args.style in p["styles"])
        category_match = bool(args.category and args.category in p["categories"])
        support = [s for s in card.get("audit_support", []) if s["purpose"] == args.purpose and s["profile"] == {
            "morphology": args.morphology, "action": args.action, "style": args.style, "route": args.route}]
        purpose_has_audit = any(s["purpose"] == args.purpose for s in card.get("audit_support", []))
        is_style_seed = card.get("approval", {}).get("kind") == "user-style-feedback"
        is_public_reference = card.get("status") == "reference-library" and card.get("public_export", {}).get("status") == "reference-only"
        if not purpose_has_audit and not is_style_seed and not is_public_reference:
            continue
        skus = sorted({s["sku"] for s in support})
        asset_ids = set(pattern["asset_ids"])
        tags = set(pattern.get("failure_tags", []))
        eligible.append({
            "id": card["id"], "version": card["version"], "card": str(card_path),
            "mode": "reuse-with-review" if action_match and style_match else "adapt-one-anchor",
            "match_points": 7 + 2 * action_match + 2 * style_match + category_match,
            "basis": {"morphology": True, "purpose": True, "route": True, "action": action_match, "style": style_match, "category_auxiliary": category_match},
            "evidence_level_for_query": "cross-product-validated" if len(skus) >= 2 else "reviewed-local" if skus else "user-style-approved" if is_style_seed else "reference-only" if is_public_reference else "adaptation-from-audited-purpose",
            "verified_skus_for_query": skus,
            "read_assets": [a for a in card["assets"] if a["id"] in asset_ids],
            "pattern": pattern,
            "failure_notes": [f for f in card["failure_notes"] if f["tag"] in tags],
            "not_inherited": card["forbidden_inheritance"]
        })
    eligible.sort(key=lambda x: (-x["match_points"], x["id"]))
    return {"mode": eligible[0]["mode"] if eligible else "explore", "candidates": eligible[:args.limit], "warning": "Tag match is not quality confidence. Recheck current SKU and review every output."}


def validate_visual_checks(brief, checks):
    realism = brief.get("realism")
    if realism is not None or str(brief.get("version")) == "1.4":
        require(isinstance(realism, dict) and realism.get("mode") in {"photographic", "grounded-advertising"}, "New realism brief needs an explicit supported mode")
        require(type(brief.get("review_set")) is bool, "New realism brief needs explicit boolean review_set")
    needs_physical = realism is not None or "physical_plausibility" in checks
    expected_checks = REQUIRED_PASS | OPTIONAL_CHECKS | ({"physical_plausibility"} if needs_physical else set())
    production_version = brief.get("visual_production", {}).get("version")
    if production_version in (1, 2) and brief.get("image_type") == "material":
        expected_checks |= {"material_event", "material_tension"}
    if production_version == 2 and brief.get("image_type") in {"feature", "material", "scene"}:
        expected_checks.add("non_text_tension")
    require(set(checks) == expected_checks, "Review needs all applicable explicit checks; new realism briefs require physical_plausibility")
    inactive = {
        "contact_and_operation": brief.get("composition", {}).get("action") in (None, "none", "display"),
        "spatial_type": brief.get("spatial_type", {}).get("enabled") is False,
        "effects": brief.get("effects", {}).get("enabled") is False,
        "set_consistency": brief.get("review_set") is False
    }
    for key, value in checks.items():
        require(isinstance(value, dict) and isinstance(value.get("evidence"), str) and value["evidence"].strip(), f"Concrete evidence required: {key}")
        status = value.get("status")
        allowed = {"pass", "not-applicable"} if key in OPTIONAL_CHECKS and inactive[key] else {"pass"}
        require(status in allowed, f"Review gate not passed: {key} ({status})")


def check_review(path):
    path = Path(path).resolve()
    r = read_json(path)
    require(r.get("schema_version") == 1, "Unsupported review schema")
    for key in ("review_id", "recipe_id", "sku", "purpose"):
        require(isinstance(r.get(key), str) and r[key], f"Missing review field: {key}")
    require(type(r.get("recipe_version")) is int and r["recipe_version"] > 0, "Invalid review recipe_version")
    dt = datetime.fromisoformat(r.get("reviewed_at", "").replace("Z", "+00:00"))
    require(dt.tzinfo is not None, "Review timestamp needs timezone")
    reviewer = r.get("reviewer", {})
    require(reviewer.get("kind") == "ai-vision" and reviewer.get("independent_context") is True, "Admission requires actual independent-context AI vision review, not creator self-check")
    require(reviewer.get("model_or_tool"), "Reviewer identity missing")
    refs = [r.get("brief"), r.get("output"), reviewer.get("execution_record")]
    sources = r.get("sources", [])
    require(any(s.get("role") == "product-identity" for s in sources), "Current product identity evidence missing")
    style_refs = r.get("style_references", [])
    require(style_refs and all(s.get("role") == "style-reference" for s in style_refs), "Positive style reference missing")
    refs += sources + style_refs
    for ref in refs:
        verified_file(ref, path.parent)
    receipt = read_json(verified_file(reviewer["execution_record"], path.parent))
    require(receipt.get("status") == "completed" and receipt.get("review_id") == r["review_id"], "Review execution receipt missing or unrelated")
    require(receipt.get("output_sha256") == r["output"]["sha256"], "Review receipt not bound to current output")
    require(receipt.get("model_or_tool") == reviewer["model_or_tool"] and receipt.get("independent_context") is True, "Reviewer receipt identity/context mismatch")
    require(receipt.get("returned_judgment") == r.get("judgment"), "Receipt and review judgment disagree")
    brief = read_json(verified_file(r["brief"], path.parent))
    require(str(brief.get("sku")) == r["sku"] and brief.get("image_type") == r["purpose"], "Review/brief SKU or purpose mismatch")
    exact_copy = brief.get("message", {}).get("exact_copy", [])
    if any(re.search(r"\d", str(line)) for line in exact_copy):
        require(any(s.get("role") == "copy-evidence" for s in sources), "Numerical copy needs current copy evidence")
    profile = r.get("profile", {})
    require(all(isinstance(profile.get(k), str) and profile[k] for k in ("morphology", "action", "style", "route")), "Incomplete review profile")
    checks = r.get("checks", {})
    validate_visual_checks(brief, checks)
    require(r.get("judgment") == "pass", "Overall judgment must be pass")
    require(isinstance(r.get("nonblocking_unknowns"), list), "Explicit unknowns list required")
    return r, refs


def promote(card_path, review_paths):
    card = validate_card(read_json(card_path))
    reviews = [check_review(p) for p in review_paths]
    rows = catalog()
    prior = [c for _, c in rows if c["id"] == card["id"]]
    require(not prior or card["version"] > max(c["version"] for c in prior), "Admission cannot overwrite an existing version")
    require(len({r["review_id"] for r, _ in reviews}) == len(reviews), "Duplicate review id")
    for r, _ in reviews:
        require((r["recipe_id"], r["recipe_version"]) == (card["id"], card["version"]), "Review must identify this candidate version")
        p = card["profile"]
        require(r["purpose"] in p["purposes"] and r["profile"]["morphology"] in p["morphologies"] and r["profile"]["route"] in p["routes"] and r["profile"]["style"] in p["styles"], "Review outside candidate scope")
        pattern = next(x for x in card["purpose_patterns"] if x["purpose"] == r["purpose"])
        require(r["profile"]["action"] in pattern["actions"], "Reviewed action not supported by candidate")
    final = CARDS / f"{card['id']}.v{card['version']}.json"
    bundle = ROOT / "assets" / "recipes" / card["id"] / f"v{card['version']}"
    require(not final.exists() and not bundle.exists(), "Version destination already exists")
    bundle.parent.mkdir(parents=True, exist_ok=True)
    # Stage before writing catalog. Failed checks above have no mutation side effects.
    with tempfile.TemporaryDirectory(prefix="recipe-admit-", dir=bundle.parent) as temp:
        stage = Path(temp)
        for i, a in enumerate(card["assets"]):
            src = verified_file(a, ROOT)
            name = f"anchor-{i}{src.suffix}"
            shutil.copy2(src, stage / name)
            a["file"] = (bundle / name).relative_to(ROOT).as_posix()
        card["audit_support"] = []
        for i, (r, refs) in enumerate(reviews):
            review_dir = stage / f"review-{i}"
            review_dir.mkdir()
            write_json(review_dir / "original-review.json", r)
            for j, ref in enumerate(refs):
                src = verified_file(ref, Path(review_paths[i]).resolve().parent)
                name = f"evidence-{j}{src.suffix}"
                shutil.copy2(src, review_dir / name)
                ref["file"] = name
            write_json(review_dir / "review.json", r)
            card["audit_support"].append({"review_id": r["review_id"], "sku": r["sku"], "purpose": r["purpose"], "profile": r["profile"], "record": {"file": (bundle / f"review-{i}" / "review.json").relative_to(ROOT).as_posix(), "sha256": digest(review_dir / "review.json")}})
        per_scope = defaultdict(set)
        for s in card["audit_support"]:
            per_scope[(s["purpose"], tuple(sorted(s["profile"].items())))].add(s["sku"])
        card["status"] = "cross-product-validated" if per_scope and all(len(v) >= 2 for v in per_scope.values()) else "reviewed-local"
        card["audited_purposes"] = sorted({s["purpose"] for s in card["audit_support"]})
        card["admission_note"] = "Only recorded purpose/profile combinations have AI audit support; other patterns remain style seeds. This script validates records, not image quality or authenticity of model receipts."
        shutil.copytree(stage, bundle)
    write_json(final, card)
    write_json(INDEX, compact_index(catalog()))
    return {"admitted": str(final), "status": card["status"], "audited_purposes": card["audited_purposes"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    sub.add_parser("index")
    sub.add_parser("validate")
    find = sub.add_parser("find")
    for key in ("morphology", "purpose", "route"):
        find.add_argument("--" + key, required=True)
    for key in ("action", "style", "category"):
        find.add_argument("--" + key)
    find.add_argument("--limit", type=int, choices=(1, 2), default=1)
    review = sub.add_parser("check-review")
    review.add_argument("--review", required=True)
    admission = sub.add_parser("promote")
    admission.add_argument("--card", required=True)
    admission.add_argument("--review", action="append", required=True)
    args = parser.parse_args()
    if args.command == "find":
        result = find_recipes(args)
    elif args.command == "check-review":
        r, _ = check_review(args.review)
        result = {"eligible": True, "review_id": r["review_id"], "scope": r["purpose"], "note": "Record and file integrity only; not proof of AI execution or image correctness."}
    elif args.command == "promote":
        result = promote(args.card, args.review)
    else:
        rows = catalog()
        expected = compact_index(rows)
        if args.command == "index":
            write_json(INDEX, expected)
            result = {"indexed_versions": len(rows)}
        elif args.command == "list":
            result = expected
        else:
            require(read_json(INDEX) == expected, "Index stale; run index after an authorized card update")
            audits = 0
            for _, c in rows:
                for support in c.get("audit_support", []):
                    review_path = verified_file(support["record"], ROOT)
                    r, _ = check_review(review_path)
                    require(r["recipe_id"] == c["id"] and r["recipe_version"] == c["version"] and r["purpose"] == support["purpose"] and r["profile"] == support["profile"] and r["sku"] == support["sku"], "Audit support mismatch")
                    audits += 1
            result = {"valid": True, "recipe_versions": len(rows), "verified_audit_records": audits, "note": "Seeds with human style approval are not independent AI audits."}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc), "admitted": False}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
