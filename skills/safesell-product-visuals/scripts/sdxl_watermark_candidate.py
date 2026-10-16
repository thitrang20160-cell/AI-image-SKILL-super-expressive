"""One explicitly authorized, lossy SDXL candidate. Execution is not removal verification."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode=True

def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as handle:
        while chunk:=handle.read(4*1024*1024): value.update(chunk)
    return value.hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True); p.add_argument('--output',required=True)
    p.add_argument('--report',required=True); p.add_argument('--model-dir',required=True)
    p.add_argument('--model-receipts',required=True); p.add_argument('--work-dir',required=True)
    p.add_argument('--strength',type=float,default=0.10)
    p.add_argument('--steps',type=int,default=50); p.add_argument('--seed',type=int,default=20261013)
    p.add_argument('--authorized-local-pixel-processing',action='store_true',required=True)
    a=p.parse_args()
    source=Path(a.input).resolve(); output=Path(a.output).resolve(); report=Path(a.report).resolve()
    work=Path(a.work_dir).resolve(); model=Path(a.model_dir).resolve()
    if not 0.02<=a.strength<=0.15 or not 20<=a.steps<=100 or int(a.strength*a.steps)<1:
        raise ValueError('Outside bounded low-strength candidate settings')
    if source in (output,report) or output==report or output.exists() or report.exists():
        raise ValueError('Use separate, new output and receipt paths')
    if output.suffix.lower()!='.png' or source.suffix.lower()!='.png':
        raise ValueError('This calibrated route accepts opaque RGB PNG only')
    output.relative_to(work); report.relative_to(work); model.relative_to(work)
    for name in ('temp','hf-cache','torch-cache','cuda-cache'): (work/name).mkdir(parents=True,exist_ok=True)
    os.environ.update(TEMP=str(work/'temp'),TMP=str(work/'temp'),HF_HOME=str(work/'hf-cache'),
        TORCH_HOME=str(work/'torch-cache'),CUDA_CACHE_PATH=str(work/'cuda-cache'),
        HF_HUB_CACHE=str(work/'hf-cache/hub'),HUGGINGFACE_HUB_CACHE=str(work/'hf-cache/hub'),
        HF_ASSETS_CACHE=str(work/'hf-cache/assets'),XDG_CACHE_HOME=str(work/'hf-cache'),
        HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_IMPLICIT_TOKEN='1')
    os.environ.pop('TRANSFORMERS_CACHE',None)
    from PIL import Image,ImageOps
    import numpy as np
    import torch
    from diffusers import StableDiffusionXLImg2ImgPipeline,EulerDiscreteScheduler
    resources=json.loads(Path(a.model_receipts).read_text(encoding='utf-8'))
    for item in resources['files']:
        path=Path(item['path']).resolve(); path.relative_to(model)
        if digest(path)!=item['sha256']: raise ValueError('Model resource changed')
    source_sha=digest(source)
    with Image.open(source) as im:
        if im.mode!='RGB' or im.info.get('transparency') is not None:
            raise ValueError('Opaque RGB source required; no silent flattening')
        if im.getexif().get(274,1)!=1: raise ValueError('Non-default orientation is outside this route')
        image=im.copy(); icc=im.info.get('icc_profile')
    width,height=image.size
    if min(width,height)<512 or max(width,height)>1600: raise ValueError('Outside 512-1600 pixel pilot range')
    # Pad to the latent grid. Crop only this added border after processing; never crop source content.
    pad_right=(-width)%8; pad_bottom=(-height)%8
    pixels=np.asarray(image)
    padded=Image.fromarray(np.pad(pixels,((0,pad_bottom),(0,pad_right),(0,0)),mode='edge'))
    if not torch.cuda.is_available(): raise RuntimeError('CUDA runtime unavailable; no silent CPU fallback')
    start=time.monotonic()
    pipe=StableDiffusionXLImg2ImgPipeline.from_pretrained(str(model),local_files_only=True,
        torch_dtype=torch.float16,variant='fp16',use_safetensors=True,add_watermarker=False)
    pipe.scheduler=EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    if pipe.watermark is not None: raise RuntimeError('Unexpected output watermark writer is enabled')
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    generator=torch.Generator(device='cpu').manual_seed(a.seed)
    with torch.inference_mode():
        candidate=pipe(prompt='',negative_prompt=None,image=padded,strength=a.strength,
            num_inference_steps=a.steps,guidance_scale=0.0,generator=generator,
            original_size=padded.size[::-1],target_size=padded.size[::-1],
            crops_coords_top_left=(0,0)).images[0]
    candidate=candidate.crop((0,0,width,height))
    if candidate.mode!='RGB' or candidate.size!=image.size: raise ValueError('Candidate geometry/mode changed')
    output.parent.mkdir(parents=True,exist_ok=True)
    candidate.save(output,format='PNG',icc_profile=icc)
    with Image.open(output) as saved:
        actual=np.asarray(saved); assert saved.size==image.size and saved.mode=='RGB'
    delta=actual.astype(np.float64)-pixels.astype(np.float64)
    mse=float(np.mean(delta*delta)); changed=bool(np.any(delta))
    if digest(source)!=source_sha: raise ValueError('Source changed')
    result={'schema_version':1,'kind':'pixel_processing_execution','status':'completed',
        'completed_at':datetime.now(timezone.utc).isoformat(),
        'input':{'file':str(source),'sha256':source_sha},'output':{'file':str(output),'sha256':digest(output)},
        'method':'SDXL low-strength img2img reconstruction','experimental':True,
        'model':{'directory':str(model),'revision':resources['revision'],'receipts_sha256':digest(a.model_receipts)},
        'implementation':{'file':str(Path(__file__).resolve()),'sha256':digest(__file__)},
        'parameters':{'strength':a.strength,'steps':a.steps,'seed':a.seed,'guidance_scale':0.0,
            'prompt':'','add_watermarker':False,'scheduler':'EulerDiscreteScheduler',
            'padding_right':pad_right,'padding_bottom':pad_bottom,'output_size':[width,height],
            'crop':'added padding only','cpu_offload':True,'vae_tiling':True},
        'runtime':{n:importlib.metadata.version(n) for n in ('torch','diffusers','transformers','accelerate','Pillow','numpy')},
        'gpu':torch.cuda.get_device_name(0),'elapsed_seconds':time.monotonic()-start,
        'original_unchanged':True,'pixels_changed':changed,
        'quality_metrics':{'mae_rgb':float(np.mean(np.abs(delta))),'rmse_rgb':mse**0.5,
            'psnr_db':10*np.log10(255**2/mse) if mse else None},
        'watermark_outcome':'unknown','removal_verified':False,'delivery_status':'working',
        'limits':['This reconstructs pixels; it does not decode and delete a known SynthID payload.',
            'Metrics do not establish product, typography or supported-watermark correctness.',
            'A current official after-check and actual preservation review are required.']}
    report.parent.mkdir(parents=True,exist_ok=True)
    with report.open('x',encoding='utf-8') as handle: json.dump(result,handle,ensure_ascii=False,indent=2)
    print(json.dumps({'output':str(output),'receipt':str(report),'pixels_changed':changed,
        'psnr_db':result['quality_metrics']['psnr_db'],'removal_verified':False},ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
