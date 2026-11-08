"""Build check against the public update service. No keys or cluster traffic."""
import json
import os
import ssl
import sys
from urllib import request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check(root, destination):
    sys.path.insert(0, root)
    from dxtalker.updates import update_ssl_context, HTTPSRedirect
    context = update_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    assert context.options & ssl.OP_NO_TLSv1 and context.options & ssl.OP_NO_TLSv1_1
    opener = request.build_opener(HTTPSRedirect(), request.HTTPSHandler(context=context))
    url = 'https://api.github.com/repos/Liberty-Chris/DX_Talker/releases?per_page=1'
    query = request.Request(url, headers={'User-Agent': 'DXTalker-XP-build-verification', 'Accept': 'application/vnd.github+json'})
    with opener.open(query, timeout=20) as response:
        data = response.read(1024 * 1024 + 1)
        assert len(data) <= 1024 * 1024
        assert isinstance(json.loads(data.decode('utf-8')), list)
    with open(destination, 'w') as stream:
        json.dump({'ok': True, 'certificate_and_hostname_validation': True,
                   'openssl': ssl.OPENSSL_VERSION, 'endpoint': url}, stream, indent=2)

if __name__ == '__main__':
    check(sys.argv[1], sys.argv[2])
