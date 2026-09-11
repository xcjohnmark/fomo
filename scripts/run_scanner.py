"""Script to execute market scanner directly."""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from app.main import main

if __name__ == "__main__":
    asyncio.run(main())
