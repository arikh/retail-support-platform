"""Load the policy files into Postgres:  uv run python scripts/ingest_policies.py"""

import asyncio
import sys
import time
from pathlib import Path

from retail_support.policy_ingest import ingest_policies

DEFAULT_DIRECTORY = Path("data/policies")


async def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIRECTORY
    start = time.perf_counter()
    count = await ingest_policies(directory)
    seconds = time.perf_counter() - start
    print(f"{count} passages from {directory} in {seconds:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
