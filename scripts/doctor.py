"""Check local resources and optional configuration without account/API access."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def check(root=None):
    root=Path(root or Path(__file__).resolve().parents[1]);manifest=json.loads((root/'assets-manifest.json').read_text(encoding='utf-8'))
    invalid=[]
    for item in manifest['original_reference_images']:
        file=root/item['file']
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']:invalid.append(item['file'])
    return {'python':sys.version.split()[0],'reference_images':len(manifest['original_reference_images']),'invalid_assets':invalid,
            'local_dependencies':{name:importlib.util.find_spec(name) is not None for name in ('PIL','yaml')},
            'optional_configuration_present':{name:bool(os.environ.get(name)) for name in ('SAFESELL_IMAGE_HOST_URL','SAFESELL_IMAGE_HOST_TOKEN','SAFESELL_API_URL','SAFESELL_API_TOKEN','WM_CLIENT_ID','WM_CLIENT_SECRET','OPENAI_API_KEY')},
            'image_generation_tool':'must be available in the invoking AI client; not a Python dependency',
            'account_or_paid_requests_performed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path);args=parser.parse_args()
    result=check(args.root);print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if not result['invalid_assets'] and all(result['local_dependencies'].values()) else 1)


if __name__=='__main__':main()
