"""Allow ``python -m ftready`` invocation."""

from __future__ import annotations

import sys

from ftready.cli import main

sys.exit(main())
