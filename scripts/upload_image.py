"""Upload to the bundled image-host contract and verify exact public GET bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request
from urllib.parse import urlparse


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def upload(image,base_url,token):
    base_url=base_url.rstrip('/');parsed=urlparse(base_url)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1','::1'))):raise ValueError('HTTPS required, except loopback tests')
    if not token:raise ValueError('Set SAFESELL_IMAGE_HOST_TOKEN')
    body=Path(image).read_bytes();digest=hashlib.sha256(body).hexdigest()
    if not 0<len(body)<=15*1024*1024:raise ValueError('Image is empty or exceeds 15 MiB')
    opener=urllib.request.build_opener(NoRedirect())
    request=urllib.request.Request(base_url+'/api/images',data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/octet-stream'},method='POST')
    with opener.open(request,timeout=45) as response:record=json.load(response)
    remote=urlparse(record.get('url',''))
    expected_prefix=base_url+'/uploads/'+digest+'.'
    if record.get('sha256')!=digest or not record.get('url','').startswith(expected_prefix) or remote.netloc!=parsed.netloc or remote.scheme!=parsed.scheme:raise ValueError('Host returned an unrelated image URL or digest')
    # Public download contains no credentials and must match complete uploaded bytes.
    with opener.open(record['url'],timeout=45) as response:
        downloaded=response.read(15*1024*1024+1);status=response.status
    if status!=200 or hashlib.sha256(downloaded).hexdigest()!=digest:raise ValueError('Public GET bytes do not match source')
    return dict(record,hostedSha256=digest,httpStatus=status,sourceFile=str(Path(image).resolve()),publicGetVerified=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',type=Path,required=True);parser.add_argument('--base-url',default=os.environ.get('SAFESELL_IMAGE_HOST_URL'))
    parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    if not args.base_url:parser.error('Set --base-url or SAFESELL_IMAGE_HOST_URL')
    if args.report.exists() or args.report.resolve()==args.image.resolve():parser.error('Use a new separate report')
    result=upload(args.image,args.base_url,os.environ.get('SAFESELL_IMAGE_HOST_TOKEN',''))
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'url':result['url'],'sha256':result['sha256'],'publicGetVerified':True}))


if __name__=='__main__':main()
