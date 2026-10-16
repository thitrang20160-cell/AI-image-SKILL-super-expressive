"""Offline public-bundle checks, relocation and loopback tests. No account/API calls."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import yaml

ROOT=Path(__file__).resolve().parents[1]


def run(args,cwd,env):
    result=subprocess.run([sys.executable,'-X','utf8','-B',*map(str,args)],cwd=cwd,env=env,text=True,encoding='utf-8',capture_output=True,timeout=240)
    if result.returncode:
        print(result.stdout);print(result.stderr,file=sys.stderr)
        raise RuntimeError('Offline command failed: '+Path(str(args[0])).name)
    return result.stdout.strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workdir',type=Path,required=True);args=parser.parse_args()
    work=args.workdir.resolve();work.mkdir(parents=True,exist_ok=True)
    runroot=Path(tempfile.mkdtemp(prefix='bundle-run-',dir=work))
    env=os.environ.copy();env['TMPDIR']=str(runroot);env['TEMP']=str(runroot);env['TMP']=str(runroot)
    # Ensure imports and package caches cannot modify checkout resources.
    env['PYTHONDONTWRITEBYTECODE']='1'
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(s in ('.git','__pycache__','.venv','work','models','data') for s in p.relative_to(ROOT).parts)]
    problems=[];link_count=0
    for file in files:
        rel=file.relative_to(ROOT).as_posix()
        if file.suffix=='.py':ast.parse(file.read_text(encoding='utf-8-sig'),filename=rel)
        if file.suffix=='.json':json.loads(file.read_text(encoding='utf-8-sig'))
        if file.suffix in ('.md','.py','.json','.yaml','.yml'):
            text=file.read_text(encoding='utf-8-sig')
            if re.search(r'(?:C|I):[/\\](?:Users|CODEX)',text,re.I):problems.append((rel,'private_machine_path'))
            if re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text):problems.append((rel,'private_key'))
            if re.search(r'\bgh[pousr]_[A-Za-z0-9_]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}',text):problems.append((rel,'credential_pattern'))
        if file.suffix=='.md':
            for link in re.findall(r'\[[^\]]+\]\(([^)\n]+)\)',file.read_text(encoding='utf-8')):
                if link.startswith(('http:','https:','#')):continue
                target=(file.parent/link.split('#',1)[0]).resolve();link_count+=1
                if not target.is_file():problems.append((rel,'missing_local_link'))
    if problems:raise ValueError('Public packaging checks failed: '+json.dumps(problems))
    for name in ('safesell-product-visuals','aliexpress-walmart-product-listing'):
        content=(ROOT/'skills'/name/'SKILL.md').read_text(encoding='utf-8');parts=content.split('---',2)
        if len(parts)<3:raise ValueError('Missing skill frontmatter')
        metadata=yaml.safe_load(parts[1])
        if metadata.get('name')!=name or not metadata.get('description'):raise ValueError('Invalid skill identity')
    manifest=json.loads((ROOT/'assets-manifest.json').read_text(encoding='utf-8'))
    listed=manifest['original_reference_images'];names=[a['file'] for a in listed]
    if len(set(names))!=len(names):raise ValueError('Duplicate manifest paths')
    for item in listed:
        path=ROOT/item['file']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Reference bytes changed')
    visual=ROOT/'skills/safesell-product-visuals/scripts';listing=ROOT/'skills/aliexpress-walmart-product-listing/scripts'
    outputs={}
    outputs['recipe_catalog']=run([visual/'recipe_library.py','validate'],ROOT,env)
    cards=json.loads(run([visual/'recipe_library.py','list'],ROOT,env))
    if not any(c['status']=='reference-library' for c in cards['recipes']):raise ValueError('Public reference scope lost')
    selected=next(c for c in cards['recipes'] if c['status']=='reference-library')
    source_card=json.loads((ROOT/'skills/safesell-product-visuals'/selected['file']).read_text(encoding='utf-8'))
    profile=source_card['profile'];pattern=source_card['purpose_patterns'][0]
    found=json.loads(run([visual/'recipe_library.py','find','--morphology',profile['morphologies'][0],'--purpose',pattern['purpose'],'--action',pattern['actions'][0],'--style',profile['styles'][0],'--route',profile['routes'][0]],ROOT,env))
    if not any(c['id']==source_card['id'] and c['evidence_level_for_query']=='reference-only' for c in found['candidates']):raise ValueError('Public reference retrieval incorrectly skipped or upgraded unaudited card')
    outputs['visual']=run([visual/'test_visual_production_gate.py','--workdir',runroot/'visual'],ROOT,env)
    outputs['batch']=run([listing/'test_audit_batch.py','--workdir',runroot/'batch'],ROOT,env)
    outputs['pricing']=run([listing/'test_pricing_curve.py','--workdir',runroot/'pricing'],ROOT,env)
    outputs['selection']=run([listing/'test_evaluate_selection.py','--workdir',runroot/'selection'],ROOT,env)
    outputs['image_host_and_install']=run([ROOT/'tests/test_image_host.py'],ROOT,env)
    outputs['non_utf8_parent']=run([ROOT/'tests/test_subprocess_encoding.py'],ROOT,env)
    outputs['installation']=run([ROOT/'scripts/install_skills.py','--target',runroot/'relocated'/'skills'],ROOT,env)
    installed=runroot/'relocated/skills'
    outputs['relocated_recipes']=run([installed/'safesell-product-visuals/scripts/recipe_library.py','validate'],runroot,env)
    outputs['relocated_batch_tests']=run([installed/'aliexpress-walmart-product-listing/scripts/test_audit_batch.py','--workdir',runroot/'relocated-batch'],runroot,env)
    receipt={'ok':True,'kind':'offline-public-bundle-validation','reference_images':len(listed),'files_checked':len(files),'local_links_checked':link_count,
             'private_data_scan':'no detected configured credential/private-path patterns; not an exhaustive legal or security certification',
             'results':outputs,'relocated_install_verified':True,'network_or_paid_service_tests':False}
    report=runroot/'bundle-verification.json';report.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'reference_images':len(listed),'files_checked':len(files),'relocated_install_verified':True,'report':str(report)},ensure_ascii=False))


if __name__=='__main__':main()
