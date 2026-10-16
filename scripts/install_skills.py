"""Install both portable skills into a chosen skill directory without overwriting."""
import argparse
import json
from pathlib import Path
import shutil


def install(target):
    source=Path(__file__).resolve().parents[1]/'skills';target=Path(target).expanduser().resolve()
    names=['safesell-product-visuals','aliexpress-walmart-product-listing']
    if any((target/name).exists() for name in names):raise ValueError('An existing skill would be overwritten; select a fresh target or back it up explicitly')
    target.mkdir(parents=True,exist_ok=True)
    for name in names:shutil.copytree(source/name,target/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    return [str(target/name/'SKILL.md') for name in names]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',type=Path,default=Path.home()/'.codex'/'skills');args=parser.parse_args()
    print(json.dumps({'installed':install(args.target)},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
