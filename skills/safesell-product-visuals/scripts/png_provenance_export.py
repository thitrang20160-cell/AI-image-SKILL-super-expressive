"""Export PNG metadata copies without raster editing or pixel-watermark removal."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

SIGNATURE = b'\x89PNG\r\n\x1a\n'
MARKERS = {
    'c2pa': b'c2pa',
    'ai_generation': b'trainedAlgorithmicMedia',
    'watermark_action': b'c2pa.watermarked.unbound',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def chunks(data):
    if data[:8] != SIGNATURE:
        raise ValueError('Only actual PNG files are supported')
    position = 8
    records = []
    while position + 12 <= len(data):
        size = struct.unpack_from('>I', data, position)[0]
        end = position + size + 12
        if end > len(data):
            raise ValueError('Truncated PNG chunk')
        kind = data[position + 4:position + 8]
        payload = data[position + 8:end - 4]
        expected_crc = struct.unpack_from('>I', data, end - 4)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != expected_crc:
            raise ValueError('PNG chunk CRC mismatch')
        records.append((kind, payload, data[position:end]))
        position = end
        if kind == b'IEND':
            if position != len(data) or size != 0:
                raise ValueError('Invalid data after IEND')
            if not records or records[0][0] != b'IHDR' or len(records[0][1]) != 13:
                raise ValueError('Invalid IHDR')
            if not any(k == b'IDAT' for k, _, _ in records):
                raise ValueError('Missing IDAT')
            return records
    raise ValueError('Missing PNG IEND')


def is_c2pa(record):
    kind, payload, _ = record
    return kind == b'caBX' and b'c2pa\x00' in payload


def retained_bytes(records):
    return SIGNATURE + b''.join(record[2] for record in records if not is_c2pa(record))


def inspect(data):
    records = chunks(data)
    # Search metadata only, not compressed pixels. This is a presence scan, not
    # a CBOR semantic decoder, signature validator or watermark detector.
    metadata = b''.join(payload for kind, payload, _ in records if kind not in (b'IDAT', b'IHDR', b'IEND', b'PLTE', b'tRNS'))
    return {
        'sha256': digest(data),
        'size_bytes': len(data),
        'chunks': [kind.decode('ascii') for kind, _, _ in records],
        'c2pa_chunk_count': sum(is_c2pa(r) for r in records),
        'metadata_marker_presence': {name: marker in metadata for name, marker in MARKERS.items()},
        'compressed_pixel_data_sha256': digest(b''.join(payload for kind, payload, _ in records if kind == b'IDAT')),
        'retained_chunks_sha256': digest(retained_bytes(records)),
        'manifest_signature_and_trust': 'not_verified',
    }


def export_copy(source, output, policy='remove-c2pa'):
    if policy not in ('remove-c2pa', 'preserve'):
        raise ValueError('Unknown metadata policy')
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError('Output must be a separate copy')
    if output.suffix.lower() != '.png':
        raise ValueError('Output extension must remain PNG')
    if output.exists():
        raise ValueError('Output already exists; choose a new version')
    original = source.read_bytes()
    before = inspect(original)
    result = retained_bytes(chunks(original)) if policy == 'remove-c2pa' else original
    after = inspect(result)
    if before['retained_chunks_sha256'] != after['retained_chunks_sha256']:
        raise ValueError('Non-C2PA chunks changed')
    if before['compressed_pixel_data_sha256'] != after['compressed_pixel_data_sha256']:
        raise ValueError('Compressed pixel data changed')
    if policy == 'remove-c2pa' and after['c2pa_chunk_count']:
        raise ValueError('C2PA block still present')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle:
        handle.write(result)
    if output.read_bytes() != result or source.read_bytes() != original:
        raise ValueError('Output write or source integrity check failed')
    remaining = any(after['metadata_marker_presence'].values())
    return {
        'schema_version': 1,
        'scope': 'container_metadata_only',
        'source': {'file': str(source), **before},
        'output': {'file': str(output), **after},
        'policy': policy,
        'metadata_status': ('needs-review' if remaining else 'removed' if before['c2pa_chunk_count'] else 'not-present') if policy == 'remove-c2pa' else 'preserved',
        'removed_c2pa_chunks': before['c2pa_chunk_count'] - after['c2pa_chunk_count'],
        'retained_chunks_identical': True,
        'compressed_pixel_data_identical': True,
        'original_unchanged': True,
        'pixel_watermark_detection': 'not_performed',
        'pixel_watermark_removal': 'not_performed',
        'delivery_status': 'working',
        'limits': ['Metadata export only; visual review and requested pixel-watermark processing are separate.',
                   'No statement of invisible-watermark absence, removal or marketplace detection.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--policy', choices=('remove-c2pa', 'preserve'), default='remove-c2pa')
    args = parser.parse_args()
    report = Path(args.report).resolve()
    if report in (Path(args.input).resolve(), Path(args.output).resolve()) or report.exists():
        raise ValueError('Report must be a new, separate file')
    record = export_copy(args.input, args.output, args.policy)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open('x', encoding='utf-8') as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    print(json.dumps({'report': str(report), 'output': record['output']['file'],
                      'metadata_status': record['metadata_status'], 'delivery_status': 'working'}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, struct.error) as exc:
        print(json.dumps({'error': str(exc), 'delivery_status': 'not_completed'}), file=sys.stderr)
        sys.exit(1)
