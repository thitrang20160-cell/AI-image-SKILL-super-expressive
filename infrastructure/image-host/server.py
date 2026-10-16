"""Small immutable image host. Bearer-authenticated uploads; public image GETs."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import warnings
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError

MAX_BYTES=15*1024*1024
Image.MAX_IMAGE_PIXELS=25_000_000
FORMATS={'PNG':('png','image/png'),'JPEG':('jpg','image/jpeg'),'WEBP':('webp','image/webp')}


def create_server(address, directory, token, public_base_url):
    if not isinstance(token,str) or len(token)<32:raise ValueError('Set an upload token of at least 32 characters')
    parsed=urlparse(public_base_url)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1'))):
        raise ValueError('Use HTTPS for a public host; HTTP is allowed only for loopback testing')
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    public_base_url=public_base_url.rstrip('/')
    write_lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup();self.connection.settimeout(30)
        def log_message(self,format,*args):pass
        def json_response(self,status,data):
            content=json.dumps(data).encode('utf-8');self.send_response(status)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(content)))
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(content)
        def do_POST(self):
            if self.path!='/api/images':return self.json_response(404,{'error':'not_found'})
            supplied=self.headers.get('Authorization','')
            if not hmac.compare_digest(supplied,'Bearer '+token):
                self.close_connection=True
                return self.json_response(401,{'error':'unauthorized'})
            try:length=int(self.headers.get('Content-Length','0'))
            except ValueError:return self.json_response(400,{'error':'invalid_length'})
            if not 0<length<=MAX_BYTES:
                self.close_connection=True
                return self.json_response(413,{'error':'invalid_upload_size'})
            body=self.rfile.read(length)
            if len(body)!=length:return self.json_response(400,{'error':'incomplete_upload'})
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('error',Image.DecompressionBombWarning)
                    with Image.open(BytesIO(body)) as image:
                        if image.format not in FORMATS or getattr(image,'n_frames',1)!=1:raise ValueError('format')
                        extension,mime=FORMATS[image.format];width,height=image.size;image.verify()
            except (OSError,ValueError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning):
                return self.json_response(422,{'error':'invalid_static_image'})
            digest=hashlib.sha256(body).hexdigest();name=digest+'.'+extension;path=directory/name
            created=False
            with write_lock:
                if path.exists():
                    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:return self.json_response(409,{'error':'stored_file_conflict'})
                else:
                    temporary=None
                    try:
                        with tempfile.NamedTemporaryFile(dir=directory,prefix='.upload-',delete=False) as handle:
                            temporary=Path(handle.name);handle.write(body);handle.flush();os.fsync(handle.fileno())
                        os.replace(temporary,path);created=True
                    finally:
                        if temporary is not None and temporary.exists():temporary.unlink()
            self.json_response(201 if created else 200,{'url':self.server.public_base_url+'/uploads/'+name,'sha256':digest,'size_bytes':len(body),'width':width,'height':height,'content_type':mime,'created':created})
        def do_GET(self):self.serve_image(False)
        def do_HEAD(self):self.serve_image(True)
        def serve_image(self,head):
            if self.path=='/health':
                if head:self.send_response(200);self.end_headers();return
                return self.json_response(200,{'status':'ok'})
            match=re.fullmatch(r'/uploads/([0-9a-f]{64})\.(png|jpg|webp)',self.path)
            if not match:return self.json_response(404,{'error':'not_found'})
            path=directory/(match.group(1)+'.'+match.group(2))
            if not path.is_file():return self.json_response(404,{'error':'not_found'})
            body=path.read_bytes()
            if hashlib.sha256(body).hexdigest()!=match.group(1):return self.json_response(409,{'error':'stored_file_conflict'})
            self.send_response(200);self.send_header('Content-Type',{'png':'image/png','jpg':'image/jpeg','webp':'image/webp'}[match.group(2)])
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','public, max-age=31536000, immutable')
            self.send_header('ETag','"'+match.group(1)+'"');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
            if not head:self.wfile.write(body)
    server=ThreadingHTTPServer(address,Handler);server.daemon_threads=True;server.public_base_url=public_base_url
    return server


def main():
    port=int(os.environ.get('PORT','8080'))
    server=create_server((os.environ.get('BIND_ADDRESS','0.0.0.0'),port),os.environ.get('IMAGE_DIRECTORY','./data/images'),os.environ.get('UPLOAD_TOKEN',''),os.environ.get('PUBLIC_BASE_URL',''))
    print(json.dumps({'service':'image-host','port':server.server_address[1],'public_downloads':True}),flush=True)
    try:server.serve_forever()
    finally:server.server_close()


if __name__=='__main__':main()
