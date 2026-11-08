from subprocess import *
import subprocess as _native

class Popen(_native.Popen):
    def __init__(self, *args, **kwargs):
        text = kwargs.pop('text', False)
        encoding = kwargs.pop('encoding', None)
        kwargs.pop('errors', None)
        if text or encoding: kwargs['universal_newlines'] = True
        _native.Popen.__init__(self, *args, **kwargs)

class CompletedProcess:
    def __init__(self, args, returncode, stdout, stderr):
        self.args, self.returncode, self.stdout, self.stderr = args, returncode, stdout, stderr
    def check_returncode(self):
        if self.returncode: raise CalledProcessError(self.returncode, self.args, self.stdout)

def run(*args, **kwargs):
    capture = kwargs.pop('capture_output', False)
    timeout = kwargs.pop('timeout', None)
    check = kwargs.pop('check', False)
    data = kwargs.pop('input', None)
    if capture:
        if 'stdout' in kwargs or 'stderr' in kwargs: raise ValueError('capture_output conflicts with explicit streams')
        kwargs['stdout'] = kwargs['stderr'] = PIPE
    if data is not None:
        if 'stdin' in kwargs: raise ValueError('input conflicts with stdin')
        kwargs['stdin'] = PIPE
    with Popen(*args, **kwargs) as process:
        try: stdout, stderr = process.communicate(data, timeout=timeout)
        except BaseException:
            process.kill(); process.communicate(); raise
        result = CompletedProcess(process.args, process.returncode, stdout, stderr)
        if check: result.check_returncode()
        return result
