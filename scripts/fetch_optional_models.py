"""Explicitly download optional public TrustMark resources, verifying pinned bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    manifest=json.loads((Path(__file__).resolve().parents[1]/'config/trustmark-models.json').read_text(encoding='utf-8'))
    root=args.output_dir.resolve();root.mkdir(parents=True,exist_ok=True)
    base=manifest['official_base_url']
    if base!='https://cai-watermark.adobe.net/watermarking/trustmark-models/':raise ValueError('Unexpected model source; revalidate explicitly')
    results=[]
    for name,expected in manifest['files'].items():
        if name not in ('decoder_Q.onnx','decoder_P.onnx','resizer.onnx'):raise ValueError('Unexpected model filename')
        target=root/name
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise ValueError('Existing model digest differs; not overwriting')
            results.append({'file':str(target),'sha256':expected,'downloaded':False});continue
        temporary=None
        try:
            digest=hashlib.sha256();total=0
            with urllib.request.urlopen(base+name,timeout=60) as response, tempfile.NamedTemporaryFile(dir=root,delete=False,prefix='.model-') as handle:
                temporary=Path(handle.name)
                while True:
                    block=response.read(1024*1024)
                    if not block:break
                    total+=len(block)
                    if total>512*1024*1024:raise ValueError('Model exceeds download bound')
                    digest.update(block);handle.write(block)
            if digest.hexdigest()!=expected:raise ValueError('Downloaded model differs from pinned implementation binding')
            # The output is explicitly selected and never replaces an existing file.
            with target.open('xb') as output, temporary.open('rb') as source:
                while True:
                    block=source.read(1024*1024)
                    if not block:break
                    output.write(block)
            results.append({'file':str(target),'sha256':expected,'downloaded':True})
        finally:
            if temporary is not None and temporary.exists():temporary.unlink()
    print(json.dumps({'models':results,'inference_or_detection_performed':False},indent=2))


if __name__=='__main__':main()
