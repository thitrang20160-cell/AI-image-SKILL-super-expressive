"""Loopback-only image-host/installer tests. Never uploads to an external service."""
import concurrent.futures
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
host=module('image_host',ROOT/'infrastructure/image-host/server.py')
client=module('image_upload',ROOT/'scripts/upload_image.py')
installer=module('skill_installer',ROOT/'scripts/install_skills.py')


class ImageHostTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.token='synthetic-loopback-only-token-0123456789'
        self.server=host.create_server(('127.0.0.1',0),self.base/'images',self.token,'http://127.0.0.1')
        self.url='http://127.0.0.1:'+str(self.server.server_port)
        self.server.public_base_url=self.url
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.image=self.base/'input.png'
        with Image.new('RGB',(24,16),(20,90,160)) as image:image.save(self.image)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3);self.temp.cleanup()
    def test_authenticated_upload_exact_public_bytes_and_idempotence(self):
        first=client.upload(self.image,self.url,self.token);second=client.upload(self.image,self.url,self.token)
        self.assertTrue(first['created']);self.assertFalse(second['created']);self.assertEqual(first['url'],second['url'])
        with urllib.request.urlopen(first['url']) as response:self.assertEqual(response.read(),self.image.read_bytes())
        self.assertNotIn(self.token,first['url'])
    def test_unauthorized_upload_does_not_create_an_image(self):
        with self.assertRaises(urllib.error.HTTPError) as error:client.upload(self.image,self.url,'wrong')
        self.assertEqual(error.exception.code,401);self.assertFalse(list((self.base/'images').glob('*.png')))
    def test_nonimage_is_rejected(self):
        invalid=self.base/'invalid.png';invalid.write_bytes(b'not an image')
        with self.assertRaises(urllib.error.HTTPError) as error:client.upload(invalid,self.url,self.token)
        self.assertEqual(error.exception.code,422)
    def test_path_traversal_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+'/uploads/../input.png')
        self.assertEqual(error.exception.code,404)
    def test_concurrent_same_image_is_written_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            rows=list(pool.map(lambda _:client.upload(self.image,self.url,self.token),range(4)))
        self.assertEqual(sum(r['created'] for r in rows),1);self.assertEqual(len({r['url'] for r in rows}),1)
    def test_remote_plaintext_upload_is_rejected(self):
        with self.assertRaises(ValueError):client.upload(self.image,'http://images.example.com',self.token)
    def test_host_requires_a_strong_configured_token(self):
        with self.assertRaises(ValueError):host.create_server(('127.0.0.1',0),self.base/'other','short',self.url)


class InstallerTests(unittest.TestCase):
    def test_fresh_install_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'skills';paths=installer.install(target)
            self.assertEqual(len(paths),2);self.assertTrue(all(Path(p).is_file() for p in paths))
            with self.assertRaises(ValueError):installer.install(target)


if __name__=='__main__':unittest.main(verbosity=2)
