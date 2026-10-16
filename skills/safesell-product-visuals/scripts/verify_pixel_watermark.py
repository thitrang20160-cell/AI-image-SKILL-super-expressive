"""One read-only official provenance check; never modifies pixels or removes watermarks."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
import uuid

ENDPOINT = 'https://api.openai.com/v1/content_provenance_checks'


def classify(response):
    if not isinstance(response, dict) or response.get('object') != 'content_provenance_check' or not isinstance(response.get('results'), list):
        return {'outcome': 'unknown', 'state': 'invalid_response'}
    results = [r for r in response['results'] if isinstance(r, dict) and r.get('type') == 'synthid']
    if len(results) != 1 or results[0].get('outcome') not in ('detected', 'not_detected'):
        return {'outcome': 'unknown', 'state': 'missing_or_invalid_synthid_result'}
    outcome = results[0]['outcome']
    return {'outcome': outcome,
            'state': 'pending-removal' if outcome == 'detected' else 'supported-signal-not-detected'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the API credential to another host.
        return None


def check_file(path, api_key=None):
    path = Path(path).resolve()
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0]
    if mime not in ('image/png', 'image/jpeg', 'image/webp') or not data or len(data) > 50 * 1024 * 1024:
        raise ValueError('Expected a nonempty PNG, JPEG or WebP of at most 50 MiB')
    record = {
        'schema_version': 1,
        'file': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'detector': 'OpenAI Content Provenance: supported SynthID signal',
        'endpoint': ENDPOINT, 'check_status': 'not_performed',
        'outcome': 'unknown', 'state': 'unavailable',
        'pixel_watermark_removal': 'not_performed',
        'removal_implementation': 'unavailable_in_this_skill',
        'response': None,
        'limits': ['A supported signal not detected is not proof of no watermark, human authorship or platform acceptance.',
                   'This script is detection only; it never declares successful watermark removal.'],
    }
    key = api_key if api_key is not None else os.environ.get('OPENAI_API_KEY', '')
    if not key.strip():
        record['reason'] = 'OPENAI_API_KEY_not_configured'
        return record
    boundary = 'safesell-provenance-' + uuid.uuid4().hex
    filename = path.name.replace('"', '_').replace('\r', '_').replace('\n', '_')
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f'Content-Type: {mime}\r\n\r\n').encode('utf-8') + data + f'\r\n--{boundary}--\r\n'.encode('ascii')
    request = urllib.request.Request(ENDPOINT, data=body, method='POST', headers={
        'Authorization': 'Bearer ' + key,
        'Content-Type': 'multipart/form-data; boundary=' + boundary,
    })
    try:
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(request, timeout=45) as response:
            result = json.loads(response.read(1024 * 1024))
        record['response'] = result
        record.update(classify(result))
        record['check_status'] = 'completed' if record['outcome'] != 'unknown' else 'failed'
    except urllib.error.HTTPError as exc:
        record.update({'check_status': 'failed', 'reason': 'http_error', 'http_status': exc.code})
        try:
            error = json.loads(exc.read(8192)).get('error', {})
            code = str(error.get('code', ''))
            record['error_code'] = code if re.fullmatch(r'[A-Za-z0-9_-]{1,100}', code) else None
        except (ValueError, AttributeError):
            pass
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        record.update({'check_status': 'failed', 'reason': 'network_or_response_error'})
    if path.read_bytes() != data:
        record.update({'check_status': 'failed', 'outcome': 'unknown', 'state': 'file_changed', 'reason': 'file_changed_during_check'})
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    report = Path(args.report).resolve()
    if report == Path(args.input).resolve() or report.exists():
        raise ValueError('Report must be a new, separate file')
    result = check_file(args.input)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    print(json.dumps({'report': str(report), 'check_status': result['check_status'],
                      'outcome': result['outcome'], 'state': result['state']}))
    return 0 if result['check_status'] == 'completed' else 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc), 'outcome': 'unknown', 'check_status': 'failed'}), file=sys.stderr)
        sys.exit(2)
