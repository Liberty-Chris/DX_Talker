"""Apply only friendly labels and a managed download table to existing releases."""
import argparse
import json
import os
from urllib import request
from release_assets import REPOSITORY, downloads, label

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('GitHub metadata requests must not redirect')


def reconcile(release, apply, call):
    if release.get('draft'): return []
    assets = release.get('assets', [])
    body = release.get('body') or ''
    updated = downloads(body, assets)
    changes = []
    for asset in assets:
        friendly = label(asset['name'])
        if friendly is not None and asset.get('label') != friendly:
            identifier = asset['id']
            if type(identifier) is not int or identifier <= 0: raise ValueError('Invalid asset ID')
            if apply: call('PATCH', '/releases/assets/' + str(identifier), {'label': friendly})
            changes.append({'asset': asset['name'], 'label': friendly})
    if updated != body:
        identifier = release['id']
        if type(identifier) is not int or identifier <= 0: raise ValueError('Invalid release ID')
        if apply: call('PATCH', '/releases/' + str(identifier), {'body': updated})
        changes.append({'download_table': True})
    return changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', default='release-download-labels.json')
    options = parser.parse_args()
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY: raise ValueError('This maintenance task is restricted to the DX Talker repository')
    token = os.environ.get('GH_TOKEN')
    if not token: raise ValueError('A repository token is required')
    opener = request.build_opener(NoRedirect())
    def call(method, suffix, payload=None):
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = request.Request('https://api.github.com/repos/' + REPOSITORY + suffix, data=data, method=method,
            headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28'})
        with opener.open(req, timeout=30) as response: return json.load(response)
    report = []
    try:
        for page in range(1, 21):
            releases = call('GET', '/releases?per_page=100&page=' + str(page))
            if not isinstance(releases, list): raise ValueError('Invalid release list')
            for release in releases:
                changes = reconcile(release, options.apply, call)
                report.append({'version': release['tag_name'], 'changes': changes})
                print(release['tag_name'] + ': ' + str(len(changes)) + ' metadata changes')
            if len(releases) < 100: break
        else: raise ValueError('Release pagination exceeded the maintenance bound')
    finally:
        with open(options.report, 'w', encoding='utf-8') as output: json.dump({'applied': options.apply, 'releases': report}, output, indent=2)


if __name__ == '__main__': main()
