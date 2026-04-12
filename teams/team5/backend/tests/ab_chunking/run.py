"""CLI entry point for running the chunking AB test.

Usage:
    cd teams/team5/backend
    python -m tests.ab_chunking.run              # run all
    python -m tests.ab_chunking.run --source kanker_nl  # kanker.nl only
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from tests.ab_chunking.harness import run_all_kanker_nl
from tests.ab_chunking.report import save_results

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = str(Path(__file__).resolve().parent / "results")


async def main(source: str = "all"):
    logger.info("=== Chunking AB Test ===")

    if source in ("all", "kanker_nl"):
        logger.info("Running kanker.nl variants...")
        kn_results = await run_all_kanker_nl()
        json_path, md_path = save_results(kn_results, "kanker_nl", RESULTS_DIR)
        logger.info("Results saved: %s", json_path)
        logger.info("Report saved: %s", md_path)

        # Print report to stdout
        with open(md_path) as f:
            print(f.read())

    logger.info("=== Done ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run chunking AB test")
    parser.add_argument("--source", choices=["all", "kanker_nl", "publications"], default="all")
    args = parser.parse_args()
    asyncio.run(main(args.source))
