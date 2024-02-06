import argparse
import logging
import sys

from gsc_bulk_indexer.auth import get_access_token
from gsc_bulk_indexer.indexer import BulkIndexer
from gsc_bulk_indexer.utils import logger


def get_args():
    parser = argparse.ArgumentParser(
        description="Submit URLs to Google Search Console for indexing"
    )
    parser.add_argument(
        "-p",
        "--property",
        help="Google Search Console property",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--credentials",
        help="Path to the service account credentials file",
        default="./service_account.json",
    )
    parser.add_argument(
        "--use-cached-urls",
        action="store_true",
        default=False,
        help="Use cached URLs from previous run. This will speed things up if "
        "you have run the script on the same domain before. This will not "
        "consider any newly added URLs.",
    )
    args = parser.parse_args()

    return args


def setup_logger():
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)


def main():
    setup_logger()
    args = get_args()
    logger.debug("🔐 Getting access token...")

    access_token = get_access_token(credentials=args.credentials)
    if access_token is None:
        logger.error("❌ Failed to get access token")
        sys.exit(1)
    logger.info("🔐 Access token acquired")

    indexer = BulkIndexer(
        access_token,
        property=args.property,
        use_cache=True,
        use_cached_urls=args.use_cached_urls,
    )

    indexer.index()
    logger.info(
        "Built by Konigle(https://konigle.com). Konigle is a website builder "
        "for SEO focused websites."
    )


if __name__ == "__main__":
    sys.exit(main())
