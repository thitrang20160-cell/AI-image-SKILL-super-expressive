"""Read-only TrustMark Q/P ONNX decoding. This is not a SynthID detector."""
import hashlib
import json
from pathlib import Path
import sys

SOURCE_COMMIT = '59bde8b41c973d2fac3be7ef89e3ac0fea2254fa'
MODEL_SHA256 = {
    'decoder_Q.onnx': 'ee3268f057c9dabef680e169302f5973d0589feea86189ed229a896cc3aa88df',
    'decoder_P.onnx': 'be6d7c33f8a7b376f179e75f3f7c58ff816a9ac7bb6d37fd0a729a635f624c35',
    'resizer.onnx': 'e7d6014def382e20d3748fc793761bfddce62578a5905fa6ef3d348c69a787c3',
}
VARIANTS = {'Q': (256, False), 'P': (224, True)}


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return {p: sha_file(root / p) for p in
            ('trustmark_local.py', '_trustmark_ecc/datalayer.py', '_trustmark_ecc/bchecc.py')}


class TrustMarkDecoder:
    def __init__(self, model_dir, runtime_dir=None):
        if runtime_dir:
            sys.path.insert(0, str(Path(runtime_dir).resolve()))
        import onnxruntime as ort
        import numpy as np
        from _trustmark_ecc.datalayer import DataLayer
        self.np = np
        self.model_dir = Path(model_dir).resolve()
        self.model_hashes = {name: sha_file(self.model_dir / name) for name in MODEL_SHA256}
        if self.model_hashes != MODEL_SHA256:
            raise ValueError('TrustMark model digest mismatch; revalidate a new model version explicitly')
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        self.sessions = {variant: ort.InferenceSession(str(self.model_dir / f'decoder_{variant}.onnx'),
                         options, providers=['CPUExecutionProvider']) for variant in VARIANTS}
        self.resize = ort.InferenceSession(str(self.model_dir / 'resizer.onnx'), options,
                                          providers=['CPUExecutionProvider'])
        self.layer = DataLayer(100, verbose=False)
        self.fingerprint = {'model_sha256': self.model_hashes, 'implementation_sha256': implementation_hashes(),
                            'onnxruntime_version': ort.__version__, 'provider': 'CPUExecutionProvider',
                            'source_commit': SOURCE_COMMIT}
        self.validation = None

    def _packet(self, scores):
        np = self.np
        if scores.shape != (1, 100) or not np.isfinite(scores).all():
            raise ValueError('Invalid ONNX decoder output')
        bits = (scores >= 0).astype(np.int64)
        payload, valid, version = self.layer.decode_bitstream(bits, MODE='binary')[0]
        predicted_version = int(version)
        # Adobe's JS decoder also tries alternate ECC schemas when footer bits are corrupt.
        if not valid:
            for alternate in (0, 1, 2):
                if alternate == predicted_version:
                    continue
                alternate_bits = bits.copy()
                alternate_bits[0, -2:] = [alternate >> 1, alternate & 1]
                payload, valid, version = self.layer.decode_bitstream(alternate_bits, MODE='binary')[0]
                if valid:
                    break
        return {'ecc_valid': bool(valid), 'encoding_schema': int(version) if valid else None,
                'predicted_schema': predicted_version, 'ecc_schema_fallback': bool(valid and version != predicted_version),
                'payload_length': len(payload) if valid else None,
                'payload_sha256': hashlib.sha256(payload.encode('ascii')).hexdigest() if valid else None,
                'raw_bits_sha256': hashlib.sha256(bits.astype('uint8').tobytes()).hexdigest()}

    def decode(self, path):
        from PIL import Image
        np = self.np
        with Image.open(path) as image:
            if image.format not in ('PNG', 'JPEG', 'WEBP') or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Only static PNG/JPEG/WebP are supported')
            if 'exif' in image.info and image.getexif().get(274, 1) != 1:
                raise ValueError('Non-default EXIF orientation needs a separately validated decoder path')
            if 'transparency' in image.info or ('A' in image.getbands() and image.getextrema()[-1][0] != 255):
                raise ValueError('Transparent imagery is outside the validated decoder input profile')
            pil_rgb = image.convert('RGB')
            rgb = np.asarray(pil_rgb, dtype=np.float32) / np.float32(255)
        tensor = np.ascontiguousarray(rgb.transpose(2, 0, 1)[None])
        h, w = rgb.shape[:2]
        result = {}
        for variant, (target, square) in VARIANTS.items():
            crop = tensor
            if w >= h and (w / h > 2 or square):
                offset = (w - h) // 2
                crop = tensor[:, :, :, offset:offset+h]
            elif w < h and (w / h < .5 or square):
                offset = (h - w) // 2
                crop = tensor[:, :, offset:offset+w, :]
            ch, cw = crop.shape[2:]
            # Port of Adobe's JS computeScalesFixed; normalization is inside resizer.onnx.
            scales = np.array([1, 1, (target + .5) / ch, (target + .5) / cw], dtype=np.float32)
            resized = self.resize.run(['Y'], {'X': np.ascontiguousarray(crop), 'scales': scales,
                                      'target_size': np.array([target], dtype=np.int64)})[0]
            if resized.shape != (1, 3, target, target) or not np.isfinite(resized).all():
                raise ValueError('Invalid ONNX resize output')
            scores = self.sessions[variant].run(['output'], {'image': resized})[0]
            onnx_packet = self._packet(scores)
            # Fixed second read-only preprocessing path from the Python implementation.
            # Small resampling differences can create chance ECC hits. Such disagreement is unknown,
            # never a confirmed positive or a silently cleared negative. No image is written.
            pil_crop = pil_rgb
            if square or w/h > 2 or w/h < .5:
                edge = min(w, h)
                x, y = (w-edge)//2, (h-edge)//2
                pil_crop = pil_rgb.crop((x, y, x+edge, y+edge))
            arr = np.asarray(pil_crop.resize((target, target), Image.Resampling.BILINEAR), dtype=np.float32)/127.5-1
            pil_tensor = np.ascontiguousarray(arr.transpose(2, 0, 1)[None])
            pil_packet = self._packet(self.sessions[variant].run(['output'], {'image': pil_tensor})[0])
            consistent = bool(onnx_packet['ecc_valid'] and pil_packet['ecc_valid']
                              and onnx_packet['payload_sha256'] == pil_packet['payload_sha256'])
            any_hit = onnx_packet['ecc_valid'] or pil_packet['ecc_valid']
            result[variant] = {
                'outcome': 'detected' if consistent else ('unknown' if any_hit else 'not_detected'),
                'ecc_valid': consistent, 'payload_consistent_across_preprocessing': consistent,
                'state': 'payload-consistent-hit' if consistent else ('unstable-ecc-hit-needs-review' if any_hit else 'no-ecc-hit'),
                'onnx_resize': onnx_packet, 'pil_bilinear': pil_packet,
                'resolution': target, 'center_square_crop': square or w/h > 2 or w/h < .5,
            }
        return result

    def validate_controls(self, manifest):
        """Run author positive/negative controls; expected results are never detector output."""
        manifest = Path(manifest).resolve()
        specs = json.loads(manifest.read_text(encoding='utf-8'))
        rows = []
        positive = {v: 0 for v in VARIANTS}
        negative = {v: 0 for v in VARIANTS}
        if not isinstance(specs, list) or not specs:
            raise ValueError('Control manifest must be a nonempty list')
        for case in specs:
            path = Path(case['file']).resolve()
            before = sha_file(path)
            if before != case['sha256']:
                raise ValueError('Control digest mismatch')
            actual = self.decode(path)
            for variant, expected in case['expected'].items():
                if variant not in VARIANTS or expected not in ('detected', 'not_detected'):
                    raise ValueError('Invalid control expectation')
                (positive if expected == 'detected' else negative)[variant] += 1
            passed = all(actual[v]['outcome'] == e for v, e in case['expected'].items())
            if sha_file(path) != before:
                passed = False
            rows.append({'file': str(path), 'sha256': before, 'expected': case['expected'],
                         'actual': actual, 'passed': passed})
        passed = all(r['passed'] for r in rows) and all(positive[v] and negative[v] for v in VARIANTS)
        self.validation = {'status': 'passed' if passed else 'failed', 'fingerprint': self.fingerprint,
                           'manifest': {'file': str(manifest), 'sha256': sha_file(manifest)},
                           'positive_expectations': positive, 'negative_expectations': negative, 'controls': rows,
                           'limits': 'Controls validate this integration; they do not estimate universal accuracy or absence.'}
        return self.validation

    def report(self, path):
        record = {'kind': 'pixel_watermark', 'detector': 'TrustMark Q/P local ONNX',
                  'supported_variants': list(VARIANTS), 'check_status': 'not_performed', 'outcome': 'unknown',
                  'fingerprint': self.fingerprint, 'integration_validation': self.validation,
                  'pixel_watermark_removal': 'not_performed',
                  'limits': ['Only TrustMark Q/P in the validated input profile are checked; this is not SynthID.',
                             'ECC validation is required. A negative is not proof of universal absence.']}
        if not self.validation or self.validation['status'] != 'passed':
            record['reason'] = 'positive_and_negative_controls_not_passed'
            return record
        try:
            record['variants'] = self.decode(path)
            record['check_status'] = 'completed'
            outcomes = [v['outcome'] for v in record['variants'].values()]
            record['outcome'] = 'detected' if 'detected' in outcomes else ('unknown' if 'unknown' in outcomes else 'not_detected')
            if record['outcome'] == 'unknown':
                record['reason'] = 'unstable_ecc_hit_needs_independent_confirmation'
        except Exception:
            record['check_status'] = 'failed'
            record['reason'] = 'decode_or_input_profile_error'
        return record
