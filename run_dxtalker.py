"""Entry point for source use and the Windows frozen package."""
from dxtalker.app import main
from dxtalker.selftest import run
import sys

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        if sys.platform.startswith('linux'):
            from dxtalker.linux_selftest import run as linux_run
            raise SystemExit(linux_run(sys.argv[2]))
        raise SystemExit(run(sys.argv[2]))
    main()
