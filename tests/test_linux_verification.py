from io import BytesIO
import ssl
import unittest
from unittest.mock import patch
from urllib import request

from dxtalker.linux_selftest import verify_release_https


class LinuxVerificationTests(unittest.TestCase):
    def test_job_token_uses_fixed_api_url_and_cannot_follow_redirects(self):
        context = ssl.create_default_context()
        with patch.dict('os.environ', {'DXTALKER_VERIFY_GITHUB_TOKEN': 'synthetic-token'}), \
                patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = BytesIO(b'[]')
            verify_release_https(context)
        query = build.return_value.open.call_args.args[0]
        self.assertEqual(query.full_url, 'https://api.github.com/repos/Liberty-Chris/DX_Talker/releases?per_page=1')
        self.assertEqual(query.get_header('Authorization'), 'Bearer synthetic-token')
        redirect, https = build.call_args.args
        self.assertIsNone(redirect.redirect_request(query, None, 302, 'redirect', {}, 'https://other.example'))
        self.assertIs(https._context, context)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_unauthenticated_verification_still_validates_release_payload(self):
        with patch.dict('os.environ', {}, clear=True), patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = BytesIO(b'{}')
            with self.assertRaises(AssertionError):
                verify_release_https(ssl.create_default_context())
        self.assertIsNone(build.return_value.open.call_args.args[0].get_header('Authorization'))
