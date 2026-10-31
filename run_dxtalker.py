"""Entry point for source use and the Windows frozen package."""
from dxtalker.app import main
from dxtalker.selftest import run
import sys

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        raise SystemExit(run(sys.argv[2]))
    main()
