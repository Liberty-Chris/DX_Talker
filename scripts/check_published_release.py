"""An existing complete release makes an exact publication retry a successful no-op.

No tag, asset or release is changed here. Exit 3 means GitHub explicitly returned
404 so the workflow may create a release. Other failures stop publication.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys


class PublicationError(ValueError):
    pass


def check_target(tag, commit, existing):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?', tag):
        raise PublicationError('Invalid release tag')
    if not re.fullmatch(r'[0-9a-f]{40}', commit) or (existing and not re.fullmatch(r'[0-9a-f]{40}', existing)):
        raise PublicationError('Invalid release commit')
    if existing and existing != commit:
        raise PublicationError(f'{tag} already belongs to another commit. Increase the application version and aligned release metadata before publishing new changes. Existing downloads were preserved.')


def inspect_release(tag, directory, repository, run=subprocess.run):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?',tag):
        raise PublicationError('Invalid release tag')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise PublicationError('Missing or invalid release repository')
    expected={p.name for p in Path(directory).iterdir() if p.is_file()}
    if not expected or 'SHA256SUMS.txt' not in expected:
        raise PublicationError('Prepared release assets or checksums are missing')
    result=run(['gh','api',f'repos/{repository}/releases/tags/{tag}'],capture_output=True,text=True,check=False)
    try:data=json.loads(result.stdout)
    except (ValueError,TypeError):
        raise PublicationError('Could not inspect the existing release. Check GitHub connectivity and token permissions.') from None
    if result.returncode:
        if isinstance(data,dict) and str(data.get('status'))=='404':return None
        raise PublicationError('GitHub could not verify the existing release. Publication stopped without changing assets.')
    if not isinstance(data,dict) or data.get('tag_name')!=tag or data.get('draft') is not False:
        raise PublicationError('An existing draft or unexpected release needs operator review before publication')
    assets=data.get('assets')
    if not isinstance(assets,list):raise PublicationError('Existing release asset metadata is invalid')
    uploaded={a.get('name') for a in assets if isinstance(a,dict) and a.get('state')=='uploaded'
              and type(a.get('size')) is int and a['size']>0}
    missing=expected-uploaded
    if missing:raise PublicationError('Existing release is incomplete. Review its assets before retrying: '+', '.join(sorted(missing)))
    return f'https://github.com/{repository}/releases/tag/{tag}'


def main():
    try:
        if len(sys.argv)==5 and sys.argv[1]=='--check-target':
            check_target(*sys.argv[2:]);return 0
        if len(sys.argv)!=3:raise PublicationError('Expected release tag and prepared asset folder')
        url=inspect_release(sys.argv[1],sys.argv[2],os.environ.get('GITHUB_REPOSITORY',''))
        if url is None:return 3
        message=f'{sys.argv[1]} is already published with all expected assets. Existing downloads were preserved. {url}'
        print('::notice::'+message)
        summary=os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary,'a',encoding='utf-8') as out:out.write(message+'\n')
        return 0
    except (PublicationError,OSError) as exc:
        print(str(exc),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
