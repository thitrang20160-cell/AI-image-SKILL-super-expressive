"""Read-only, hash-bound multi-signal audit; no universal clean score or pixel edits.

Cloud checks require an explicit --cloud selection and local environment credentials.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
import uuid

from png_provenance_export import inspect
from trustmark_local import TrustMarkDecoder
from verify_pixel_watermark import check_file, NoRedirect

ENDPOINTS = {'hive': 'https://api.thehive.ai/api/v2/task/sync',
             'sightengine': 'https://api.sightengine.com/1.0/check.json'}
REQUIRED_PIXEL_DETECTORS = ('openai_synthid', 'trustmark_qp')


def probability(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Invalid model probability')
    return float(value)


def parse_classifier(provider, response):
    """Returns only validated classifier evidence, never a watermark verdict."""
    if not isinstance(response, dict):
        raise ValueError('Expected an object')
    if provider == 'sightengine':
        if response.get('status') != 'success' or not isinstance(response.get('type'), dict):
            raise ValueError('Missing successful classification')
        score = probability(response['type'].get('ai_generated'))
        receipt = {'status': 'success', 'type': {'ai_generated': score}}
    elif provider == 'hive':
        statuses = response.get('status')
        if not isinstance(statuses, list) or len(statuses) != 1 or not isinstance(statuses[0], dict):
            raise ValueError('Expected one image classification status')
        item = statuses[0]
        if (not isinstance(item.get('status'), dict) or type(item['status'].get('code')) not in (str, int)
                or item['status']['code'] not in ('0', 0)):
            raise ValueError('Hive did not report success')
        body = item.get('response')
        if not isinstance(body, dict) or not isinstance(body.get('output'), list) or len(body['output']) != 1:
            raise ValueError('Expected one image frame')
        frame = body['output'][0]
        if not isinstance(frame, dict) or not isinstance(frame.get('classes'), list):
            raise ValueError('Missing Hive classes')
        scores = {}
        for item in frame['classes']:
            if not isinstance(item, dict):
                raise ValueError('Invalid class')
            label = item.get('class')
            if label in ('ai_generated', 'not_ai_generated'):
                if label in scores:
                    raise ValueError('Duplicated AI class')
                scores[label] = probability(item.get('score'))
        if set(scores) != {'ai_generated', 'not_ai_generated'} or abs(sum(scores.values()) - 1) > .02:
            raise ValueError('Missing or inconsistent AI classification head')
        score = scores['ai_generated']
        receipt = {'status_code': 0, 'classes': scores}
    else:
        raise ValueError('Unknown provider')
    return {'ai_generated_probability': score, 'receipt': receipt}


def cloud_classifier(path, provider, enabled=False):
    path = Path(path).resolve()
    result = {'kind': 'ai_classifier', 'detector': provider, 'endpoint': ENDPOINTS[provider],
              'check_status': 'not_performed', 'ai_generated_probability': None,
              'watermark_outcome': 'not_applicable', 'live_request_attempted': False,
              'limits': ['AI probability is not a watermark verdict, a Walmart decision, or proof of authorship.']}
    if not enabled:
        result['reason'] = 'cloud_check_not_requested'
        return result
    fields = {}
    headers = {'Accept': 'application/json'}
    if provider == 'hive':
        key = os.environ.get('HIVE_API_KEY', '').strip()
        if not key:
            result['reason'] = 'HIVE_API_KEY_not_configured'
            return result
        headers['Authorization'] = 'Token ' + key
    else:
        user, secret = os.environ.get('SIGHTENGINE_API_USER', '').strip(), os.environ.get('SIGHTENGINE_API_SECRET', '').strip()
        if not user or not secret:
            result['reason'] = 'SIGHTENGINE_credentials_not_configured'
            return result
        fields = {'models': 'genai', 'api_user': user, 'api_secret': secret}
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0]
    if mime not in ('image/png', 'image/jpeg', 'image/webp') or not data or len(data) > 50*1024*1024:
        result.update({'check_status': 'failed', 'reason': 'input_format_or_size_unsupported'})
        return result
    boundary = 'safesell-signals-' + uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    filename = path.name.replace('"', '_').replace('\r', '_').replace('\n', '_')
    body.extend((f'--{boundary}\r\nContent-Disposition: form-data; name="media"; filename="{filename}"\r\n'
                 f'Content-Type: {mime}\r\n\r\n').encode())
    body.extend(data)
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    headers['Content-Type'] = 'multipart/form-data; boundary=' + boundary
    req = urllib.request.Request(ENDPOINTS[provider], bytes(body), headers, method='POST')
    result['live_request_attempted'] = True
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=45) as response:
            value = json.loads(response.read(1024*1024))
        result.update(parse_classifier(provider, value))
        result['check_status'] = 'completed'
        # Keep validated numerical evidence only; never save credential/header/body echoes.
    except urllib.error.HTTPError as exc:
        result.update({'check_status': 'failed', 'reason': 'http_error', 'http_status': exc.code})
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError, KeyError):
        result.update({'check_status': 'failed', 'reason': 'network_or_response_error'})
    return result


def summarize(detectors):
    outcomes = {name: detectors.get(name, {}).get('outcome', 'unknown') for name in REQUIRED_PIXEL_DETECTORS}
    completed = [name for name in REQUIRED_PIXEL_DETECTORS
                 if detectors.get(name, {}).get('check_status') == 'completed'
                 and outcomes[name] in ('detected', 'not_detected')]
    positives = [name for name in completed if outcomes[name] == 'detected']
    unknown = [name for name in REQUIRED_PIXEL_DETECTORS if name not in completed]
    return {'profile': 'safesell-expanded-v1', 'required_pixel_detectors': list(REQUIRED_PIXEL_DETECTORS),
            'completed_pixel_detectors': completed, 'detected_pixel_signals': positives,
            'unknown_pixel_detectors': unknown,
            'supported_pixel_outcome': 'detected' if positives else ('unknown' if unknown else 'not_detected'),
            'coverage_status': 'partial' if unknown else 'profile_completed',
            'universal_watermark_absence': 'not_established', 'platform_acceptance': 'not_established'}


def audit(path, trustmark=None, cloud=()):
    path = Path(path).resolve()
    before = path.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    detectors = {}
    if before.startswith(b'\x89PNG\r\n\x1a\n'):
        try:
            meta = inspect(before)
            detectors['png_c2pa'] = {'kind': 'container_provenance', 'check_status': 'completed',
                    'outcome': 'detected' if meta['c2pa_chunk_count'] else 'not_detected',
                    'c2pa_chunk_count': meta['c2pa_chunk_count'], 'metadata_markers': meta['metadata_marker_presence'],
                    'limits': ['PNG C2PA container presence only; no signature validation or all-format claim.']}
        except (ValueError, OSError):
            detectors['png_c2pa'] = {'kind': 'container_provenance', 'check_status': 'failed', 'outcome': 'unknown'}
    else:
        detectors['png_c2pa'] = {'kind': 'container_provenance', 'check_status': 'not_performed',
                                'outcome': 'unknown', 'reason': 'not_a_png'}
    detectors['trustmark_qp'] = trustmark.report(path) if trustmark else {
        'kind': 'pixel_watermark', 'check_status': 'not_performed', 'outcome': 'unknown',
        'reason': 'validated_local_runtime_models_or_controls_unavailable'}
    detectors['openai_synthid'] = check_file(path, api_key=None if 'openai' in cloud else '')
    detectors['openai_synthid'].update({'kind': 'pixel_watermark',
           'live_request_attempted': 'openai' in cloud and bool(os.environ.get('OPENAI_API_KEY', '').strip())})
    if 'openai' not in cloud:
        detectors['openai_synthid']['reason'] = 'cloud_check_not_requested'
    for provider in ('hive', 'sightengine'):
        detectors[provider] = cloud_classifier(path, provider, provider in cloud)
    for name, url in [('google_synthid_manual', 'https://synthid.com/'),
                      ('adobe_inspect_manual', 'https://contentauthenticity.adobe.com/')]:
        detectors[name] = {'kind': 'manual_source_check', 'check_status': 'not_performed',
                           'outcome': 'unknown', 'entrypoint': url,
                           'reason': 'no_actual_upload_or_result_receipt'}
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        for result in detectors.values():
            result.update({'check_status': 'failed', 'reason': 'file_changed_during_audit'})
            if 'outcome' in result:
                result['outcome'] = 'unknown'
            if 'ai_generated_probability' in result:
                result['ai_generated_probability'] = None
    for result in detectors.values():
        result['checked_sha256'] = digest
    return {'schema_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(),
            'file': str(path), 'sha256': digest, 'detectors': detectors, 'summary': summarize(detectors),
            'pixel_watermark_removal': 'not_performed',
            'limits': ['No classifier score overrides watermark checks. No universal detector or Walmart detector is claimed.',
                       'Unknown coverage is not a negative. This audit never changes an image.']}


def validate_coverage(record, image, digest):
    """Gate consistency check; not a cryptographic authenticity proof of receipts."""
    if not isinstance(record, dict) or Path(record.get('file', '')).resolve() != Path(image).resolve() or record.get('sha256') != digest:
        raise ValueError('Coverage audit does not match the current image')
    detectors = record.get('detectors')
    if not isinstance(detectors, dict):
        raise ValueError('Missing detector evidence')
    for name in REQUIRED_PIXEL_DETECTORS:
        row = detectors.get(name)
        if not isinstance(row, dict) or row.get('checked_sha256') != digest or row.get('kind') != 'pixel_watermark':
            raise ValueError('Pixel detector evidence missing or stale')
        if name == 'trustmark_qp' and row.get('check_status') == 'completed':
            validation = row.get('integration_validation')
            variants = row.get('variants')
            if (not isinstance(validation, dict) or validation.get('status') != 'passed'
                    or validation.get('fingerprint') != row.get('fingerprint')
                    or not isinstance(variants, dict) or set(variants) != {'Q', 'P'}):
                raise ValueError('TrustMark integration evidence missing')
            for variant in variants.values():
                if not isinstance(variant, dict):
                    raise ValueError('TrustMark ECC result inconsistent')
                a, b = variant.get('onnx_resize'), variant.get('pil_bilinear')
                if not isinstance(a, dict) or not isinstance(b, dict) or any(type(p.get('ecc_valid')) is not bool for p in (a,b)):
                    raise ValueError('TrustMark preprocessing evidence missing')
                consistent = bool(a['ecc_valid'] and b['ecc_valid'] and a.get('payload_sha256')
                                  and a['payload_sha256'] == b.get('payload_sha256'))
                outcome = 'detected' if consistent else ('unknown' if a['ecc_valid'] or b['ecc_valid'] else 'not_detected')
                if variant.get('ecc_valid') is not consistent or variant.get('outcome') != outcome:
                    raise ValueError('TrustMark ECC result inconsistent')
            outcomes = [v['outcome'] for v in variants.values()]
            actual = 'detected' if 'detected' in outcomes else ('unknown' if 'unknown' in outcomes else 'not_detected')
            if actual != row.get('outcome'):
                raise ValueError('TrustMark overall result inconsistent')
        if name == 'openai_synthid' and row.get('check_status') == 'completed':
            from verify_pixel_watermark import classify, ENDPOINT
            if row.get('endpoint') != ENDPOINT or classify(row.get('response'))['outcome'] != row.get('outcome'):
                raise ValueError('OpenAI response inconsistent')
    calculated = summarize(detectors)
    if record.get('summary') != calculated:
        raise ValueError('Coverage summary inconsistent')
    return calculated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--trustmark-model-dir')
    parser.add_argument('--runtime-dir')
    parser.add_argument('--control-manifest')
    parser.add_argument('--cloud', nargs='*', choices=('openai', 'hive', 'sightengine'), default=[])
    args = parser.parse_args()
    output = Path(args.report).resolve()
    if output.exists() or output == Path(args.input).resolve():
        raise ValueError('Report must be a new separate file')
    engine = None
    if args.trustmark_model_dir and args.control_manifest:
        try:
            engine = TrustMarkDecoder(args.trustmark_model_dir, args.runtime_dir)
            engine.validate_controls(args.control_manifest)
        except Exception:
            # Optional-runtime failures remain unknown; never expose provider data or secrets.
            engine = None
    record = audit(args.input, engine, args.cloud)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'report': str(output), 'summary': record['summary']}))
    return 0 if record['summary']['coverage_status'] == 'profile_completed' else 2


if __name__ == '__main__':
    sys.exit(main())
