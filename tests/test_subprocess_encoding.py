"""Regression for a Windows CP1252 parent reading a UTF-8 image-tool subprocess."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bundle_verifier',ROOT/'scripts/verify_public_bundle.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)


class EncodingTests(unittest.TestCase):
    def test_unicode_child_output_survives_legacy_parent_encoding(self):
        with tempfile.TemporaryDirectory() as directory, patch('subprocess._text_encoding',return_value='cp1252'):
            result=verifier.run(['-c',"print('商品原图与审核')"],Path(directory),os.environ.copy())
        self.assertEqual(result,'商品原图与审核')


if __name__=='__main__':unittest.main(verbosity=2)
