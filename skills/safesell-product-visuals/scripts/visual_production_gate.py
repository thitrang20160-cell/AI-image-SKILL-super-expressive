"""Offline input/review integrity gate for local-reference commercial image production.

This validates records and bytes, not aesthetics or authenticity of claimed reviews.
It never generates, uploads, publishes, detects watermarks, or calls a paid service.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from recipe_library import validate_visual_checks


class InvalidRecord(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise InvalidRecord(code)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_file(value, base):
    require(isinstance(value, str) and bool(value.strip()), 'file_reference_missing')
    path = Path(value)
    return (path if path.is_absolute() else Path(base) / path).resolve()


def load_object(path, tracked):
    path = Path(path).resolve()
    raw = path.read_bytes()
    value = json.loads(raw.decode('utf-8-sig'))
    require(isinstance(value, dict), 'record_must_be_object')
    tracked[str(path)] = hashlib.sha256(raw).hexdigest()
    return value


def verify_ref(ref, base, tracked):
    require(isinstance(ref, dict), 'bound_file_reference_missing')
    path = resolve_file(ref.get('file'), base)
    expected = ref.get('sha256')
    require(isinstance(expected, str) and len(expected) == 64 and all(c in '0123456789abcdef' for c in expected), 'invalid_sha256')
    require(path.is_file() and digest(path) == expected, 'bound_file_changed_or_missing')
    tracked[str(path)] = expected
    return path


def _request(path, tracked):
    path = Path(path).resolve()
    request = load_object(path, tracked)
    base = path.parent
    require(type(request.get('schema_version')) is int and request['schema_version'] == 1, 'unsupported_request_schema')
    require(isinstance(request.get('sku'), str) and request['sku'].strip(), 'sku_missing')
    require(isinstance(request.get('purpose'), str) and request['purpose'].strip(), 'purpose_missing')
    require(request.get('tool') == 'built-in image_gen', 'tool_not_supported_by_local_gate')
    brief_path = verify_ref(request.get('brief'), base, tracked)
    brief = load_object(brief_path, tracked)
    require(brief.get('sku') == request['sku'] and brief.get('image_type') == request['purpose'], 'request_brief_scope_mismatch')
    require(type(brief.get('visual_production', {}).get('version')) is int and brief['visual_production']['version'] == 1, 'production_contract_version_missing')
    require(type(brief.get('review_set')) is bool, 'review_set_must_be_explicit')
    require(brief.get('realism', {}).get('mode') in ('photographic', 'grounded-advertising'), 'realism_mode_missing')
    for module in ('spatial_type', 'effects', 'material_expression'):
        require(type(brief.get(module, {}).get('enabled')) is bool, 'module_enablement_missing:' + module)
    style = brief.get('style_lock', {})
    require(type(style.get('required')) is bool, 'style_lock_policy_missing')
    if not style['required']:
        require(isinstance(style.get('reason'), str) and style['reason'].strip(), 'style_lock_exception_reason_missing')
    args = request.get('tool_args')
    require(isinstance(args, dict), 'actual_tool_args_missing')
    require(not (set(args) - {'prompt', 'referenced_image_paths', 'transparent_background'}), 'unsupported_or_unverifiable_tool_parameter')
    require(isinstance(args.get('prompt'), str) and args['prompt'].strip(), 'exact_prompt_missing')
    require(type(args.get('transparent_background')) is bool, 'background_policy_missing')
    attached = args.get('referenced_image_paths')
    require(isinstance(attached, list) and attached, 'local_reference_paths_missing')
    # Keep exact tool_args paths absolute: the tool has no request-file base directory.
    require(all(isinstance(p, str) and Path(p).is_absolute() for p in attached), 'tool_reference_paths_must_be_absolute')
    attached_paths = {resolve_file(p, base) for p in attached}
    require(len(attached_paths) == len(attached), 'duplicate_attached_reference')
    inputs = request.get('inputs')
    require(isinstance(inputs, list) and inputs, 'input_role_manifest_missing')
    roles = set()
    image_paths = set()
    style_paths = set()
    for ref in inputs:
        input_path = verify_ref(ref, base, tracked)
        role = ref.get('role')
        require(role in ('product-identity', 'verified-geometry', 'style-reference', 'draft', 'brand-asset', 'copy-evidence'), 'unknown_input_role')
        roles.add(role)
        if role not in ('copy-evidence', 'verified-geometry'):
            image_paths.add(input_path)
            require(input_path in attached_paths, 'declared_image_not_attached:' + role)
        if role == 'style-reference':
            style_paths.add(input_path)
            approval = ref.get('approval', {})
            require(approval.get('status') in ('user-approved-style', 'user-selected-reference'), 'unapproved_draft_cannot_be_style_anchor')
            verify_ref(approval.get('evidence'), base, tracked)
    require('product-identity' in roles, 'original_product_reference_missing')
    require(attached_paths == image_paths, 'attached_images_missing_role_binding')
    if request.get('mode') == 'edit':
        require('draft' in roles, 'edit_target_missing')
    else:
        require(request.get('mode') == 'generate', 'request_mode_missing')
    if style['required']:
        require(bool(style_paths), 'approved_style_reference_missing')
        require(isinstance(style.get('transfer'), list) and style['transfer'], 'style_transfer_relations_missing')
        require(isinstance(style.get('exclude'), list) and style['exclude'], 'style_exclusions_missing')
        composition = brief.get('composition', {})
        for field in ('near', 'middle', 'far', 'tension_source', 'primary_subject'):
            require(isinstance(composition.get(field), str) and composition[field].strip(), 'composition_relation_missing:' + field)
    if request['purpose'] == 'material':
        material = brief['material_expression']
        require(material['enabled'] is True and material.get('action') and material.get('visual_result'), 'material_event_missing')
    return request, brief, style_paths


def evaluate(request_path, review_path=None, expected_output=None, expected_sku=None, expected_purpose=None, expected_role=None):
    tracked = {}
    errors = []
    output = None
    reviewer = None
    try:
        request, brief, style_paths = _request(request_path, tracked)
        if expected_sku is not None:
            require(request['sku'] == expected_sku, 'expected_sku_mismatch')
        if expected_purpose is not None:
            require(request['purpose'] == expected_purpose, 'expected_purpose_mismatch')
        if expected_role is not None:
            require(request.get('slot_role') == expected_role, 'expected_slot_role_mismatch')
        if review_path is not None:
            review_path = Path(review_path).resolve()
            review = load_object(review_path, tracked)
            base = review_path.parent
            require(review.get('sku') == request['sku'] and review.get('purpose') == request['purpose'], 'review_scope_mismatch')
            require(verify_ref(review.get('generation_request'), base, tracked) == Path(request_path).resolve(), 'review_bound_to_different_request')
            require(verify_ref(review.get('brief'), base, tracked) == verify_ref(request['brief'], Path(request_path).resolve().parent, tracked), 'review_bound_to_different_brief')
            candidate = verify_ref(review.get('output'), base, tracked)
            output = {'file': str(candidate), 'sha256': tracked[str(candidate)]}
            if expected_output is not None:
                require(candidate == Path(expected_output).resolve(), 'review_bound_to_different_output')
            reviewer = review.get('reviewer', {})
            require(reviewer.get('kind') in ('creator-self-check', 'ai-vision', 'human'), 'reviewer_kind_missing')
            require(type(reviewer.get('independent_context')) is bool, 'reviewer_context_missing')
            if reviewer['kind'] == 'creator-self-check':
                require(reviewer['independent_context'] is False, 'self_check_cannot_claim_independence')
            if reviewer['independent_context']:
                receipt_path = verify_ref(reviewer.get('execution_record'), base, tracked)
                receipt = load_object(receipt_path, tracked)
                require(receipt.get('status') == 'completed' and receipt.get('output_sha256') == output['sha256'] and receipt.get('review_id') == review.get('review_id'), 'independent_review_receipt_unrelated')
            require(review.get('judgment') == 'pass' and review.get('unresolved_defects') == [], 'review_not_passed_or_defects_unresolved')
            checks = review.get('checks')
            require(isinstance(checks, dict), 'visual_checks_missing')
            validate_visual_checks(brief, checks)
            inspection = review.get('inspection', {})
            require(inspection.get('full_size') is True and inspection.get('thumbnail') is True and isinstance(inspection.get('evidence'), str) and inspection['evidence'].strip(), 'full_size_and_thumbnail_review_missing')
            comparisons = review.get('comparisons', [])
            require(isinstance(comparisons, list), 'style_comparisons_invalid')
            compared = set()
            for row in comparisons:
                require(isinstance(row, dict) and isinstance(row.get('evidence'), str) and row['evidence'].strip(), 'style_comparison_observation_missing')
                compared.add(verify_ref(row.get('reference'), base, tracked))
            require(style_paths <= compared, 'approved_style_not_actually_compared')
            exact_copy = brief.get('message', {}).get('exact_copy', [])
            require(isinstance(exact_copy, list) and review.get('observed_copy') == exact_copy, 'observed_copy_differs_from_locked_copy')
    except InvalidRecord as exc:
        errors.append(str(exc))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        errors.append('evidence_invalid_missing_or_stale')
    try:
        if any(not Path(p).is_file() or digest(p) != sha for p, sha in tracked.items()):
            errors.append('inputs_changed_during_gate')
    except OSError:
        errors.append('inputs_changed_during_gate')
    return {'schema_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(),
            'phase': 'review' if review_path is not None else 'preflight', 'ok': not errors,
            'errors': errors, 'output': output, 'reviewer': reviewer,
            'evidence': [{'file': p, 'sha256': sha} for p, sha in tracked.items()],
            'limits': 'Record/byte integrity only. Does not recognize aesthetics, authenticate claimed tool/review execution, prove user approval, run watermark checks, intercept uploads, or establish cross-SKU stability.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('preflight', 'review'))
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.phase == 'review' and args.review is None:
        parser.error('review requires --review')
    if args.phase == 'preflight' and args.review is not None:
        parser.error('preflight does not accept --review')
    result = evaluate(args.request, args.review)
    if args.report:
        report = args.report.resolve()
        protected = {Path(ref['file']).resolve() for ref in result['evidence']}
        if report in protected or report.exists():
            parser.error('Use a new separate report in your output directory, never overwrite an input or old report')
        report.parent.mkdir(parents=True, exist_ok=True)
        with report.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    sys.exit(main())
