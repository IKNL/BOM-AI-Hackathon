"""CLI entry point for running the chunking AB test.

Usage:
    cd teams/team5/backend
    python -m tests.ab_chunking.run                          # run main variants
    python -m tests.ab_chunking.run --source kanker_nl       # kanker.nl only
    python -m tests.ab_chunking.run --drilldown              # chunk-size sub-variants
"""

import argparse
import asyncio
import logging
from pathlib import Path

from tests.ab_chunking.harness import run_all_kanker_nl
from tests.ab_chunking.report import save_results

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = str(Path(__file__).resolve().parent / "results")


async def main(source: str = "all", drilldown: bool = False):
    label = "Drilldown" if drilldown else "Main"
    logger.info("=== Chunking AB Test (%s) ===", label)

    if source in ("all", "kanker_nl"):
        logger.info("Running kanker.nl variants...")
        kn_results = await run_all_kanker_nl(drilldown=drilldown)
        suffix = "kanker_nl_drilldown" if drilldown else "kanker_nl"
        json_path, md_path = save_results(kn_results, suffix, RESULTS_DIR)
        logger.info("Results saved: %s", json_path)
        logger.info("Report saved: %s", md_path)

        with open(md_path) as f:
            print(f.read())

    logger.info("=== Done ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run chunking AB test")
    parser.add_argument("--source", choices=["all", "kanker_nl", "publications"], default="all")
    parser.add_argument("--drilldown", action="store_true", help="Run chunk-size sub-variants of the winner")
    args = parser.parse_args()
    asyncio.run(main(args.source, args.drilldown))
