from io import BytesIO
import json
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from urllib.error import HTTPError

from platforms.xp import check_https


class XPHttpsTests(unittest.TestCase):
    def context(self):
        return SimpleNamespace(verify_mode=ssl.CERT_REQUIRED, check_hostname=True,
                               options=ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1)

    def test_ci_token_stays_at_fixed_endpoint_and_is_not_written_to_report(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.dict('os.environ', {'DXTALKER_VERIFY_GITHUB_TOKEN': 'synthetic-token'}), \
                patch('dxtalker.updates.update_ssl_context', return_value=self.context()), \
                patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = BytesIO(b'[]')
            destination=Path(folder)/'report.json'
            check_https.check(str(Path(__file__).resolve().parent.parent), str(destination))
            report=destination.read_text()
            self.assertTrue(json.loads(report)['ok'])
            self.assertNotIn('synthetic-token',report)
        query=build.return_value.open.call_args.args[0]
        self.assertEqual(query.get_header('Authorization'),'Bearer synthetic-token')
        self.assertEqual(query.full_url,'https://api.github.com/repos/Liberty-Chris/DX_Talker/releases?per_page=1')
        redirect,handler=build.call_args.args
        self.assertIsNone(redirect.redirect_request(query,None,302,'redirect',{},'https://other.example'))
        self.assertTrue(handler._context.check_hostname)
        self.assertEqual(handler._context.verify_mode,ssl.CERT_REQUIRED)

    def test_http_failure_still_fails_verification_without_a_report(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ',{},clear=True), \
                patch('dxtalker.updates.update_ssl_context',return_value=self.context()), \
                patch('urllib.request.build_opener') as build:
            build.return_value.open.side_effect=HTTPError('https://api.github.com',403,'rate limit',{},None)
            destination=Path(folder)/'report.json'
            with self.assertRaises(HTTPError):check_https.check(str(Path(__file__).resolve().parent.parent),str(destination))
            self.assertFalse(destination.exists())
            self.assertIsNone(build.return_value.open.call_args.args[0].get_header('Authorization'))
