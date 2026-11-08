"""Explicit CI diagnostic for native UI exits. Records code locations only."""
import os
import sys
import faulthandler

root, output = sys.argv[1:]
sys.path.insert(0, root)
import xp_support.bootstrap
log = open(output, 'w', buffering=1)
faulthandler.enable(file=log, all_threads=True)
count = 0

def trace(frame, event, argument):
    global count
    name = os.path.basename(frame.f_code.co_filename)
    if name in ('app.py', 'rounded.py', 'filter_ui.py') and event in ('call', 'line'):
        count += 1
        if count < 100000:
            log.write(name + ':' + frame.f_code.co_name + ':' + str(frame.f_lineno) + '\n')
    return trace

sys.settrace(trace)
try:
    from xp_support.selftest import run
    result = run(output + '.json')
finally:
    sys.settrace(None)
    log.close()
raise SystemExit(result)
