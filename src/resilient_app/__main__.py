"""Entry point for python -m resilient_app.

This allows running with:
    python -m resilient_app --demo
"""

from resilient_app.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
