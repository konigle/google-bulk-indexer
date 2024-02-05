import asyncio
import datetime
import itertools
import typing
from urllib.parse import urlparse

from . import gsc, parse, utils


class BulkIndexer:
    """Submits the URLs of a website for indexing in Google Search Console"""

    REQUEST_QUOTA = 200

    def __init__(
        self,
        access_token: str,
        property: str = None,
        urls: typing.List[str] = None,
        use_cache: bool = True,
        use_cached_urls: bool = False,
    ) -> None:
        """Bulk indexer for Google Search Console

        Args:
            access_token (str): Google service account oauth2 access token
            property (str, optional): GSC property to index. Needed if `urls`
                is not provided. Defaults to None.
            urls (typing.List[str], optional): List of URLs to index.
                Needed if property is not provided. Defaults to None.
            use_cache (bool, optional): Whether to use cache to store the
                indexing and notification status. Defaults to True.
            use_cached_urls (bool, optional): Whether to use cached URLs
                instead of loading sitemaps. Applicable only if `urls` is not
                provided and `use_cache` is True Defaults to False.

        Raises:
            ValueError: When both `property` and `urls` are not provided
        """
        if property is None and not urls:
            raise ValueError("Either property or urls is required")

        self._access_token = access_token
        self._use_cache = use_cache
        self._use_cached_urls = use_cached_urls
        if property is not None:
            self._property = property
        else:
            self._property = f"https://{urlparse(urls[0]).netloc}/"
        # clean the property and get the site url
        self._site_url = gsc.get_site_url(self._property)
        self._sitemaps = []
        self._urls = urls or []
        if self._use_cache:
            self._cache = utils.StatusCache(self._site_url)
        else:
            self._cache = {}  # dummy cache
        self._indexer = gsc.Indexer(self._access_token, self._site_url)
        self._cache_timeout = datetime.timedelta(days=14)
        self._status_urls_map = {}
        self._num_submitted = 0

    def index(self) -> int:

        # load cache
        if self._use_cache:
            self._cache.load()

        # get page urls if not provided during init
        if not self._urls:
            self._load_sitemaps()
            if not self._sitemaps:
                utils.logger.warning(
                    f"❌ No sitemaps found for {self._property}. Exiting..."
                )
                return 0
            if self._use_cache and self._use_cached_urls:
                self._load_cached_urls()
            else:
                self._load_urls()
        if not self._urls:
            utils.logger.warning(
                f"❌ No URLs found for {self._property}. Exiting..."
            )
            return 0
        else:
            utils.logger.info(f"Found {len(self._urls)} URLs")

        # check indexing status
        self._check_indexing_status()

        urls = self._collect_urls_for_submission()
        num_urls = len(urls)
        if not num_urls:
            utils.logger.info(
                "✨ No URLs are eligible for submission. "
                "They are already submitted or indexed"
            )
            return 0
        utils.logger.info(f"🔍 Found {num_urls} URLs for submission.")
        self._request_indexing(urls)
        utils.logger.info(
            "🚀 All done. Run this when you add new pages or update page "
            "content"
        )
        return self._num_submitted

    def _request_indexing(self, urls: typing.List[str]):
        for url in urls:
            utils.logger.info(f"👩‍💻 Working on {url}")
            current_state = self._cache.get(url) or {}
            notification_status = None
            try:
                # assuming that we will not hit this quota of 180 requests
                # per minute
                # https://developers.google.com/search/apis/indexing-api/v3/quota-pricing#quota
                notification_status = self._indexer.get_notification_status(
                    url
                )
                utils.logger.info(
                    "🕛 URL is already submitted. It may take few days for "
                    "Google to index"
                )
            except Exception:
                # getting notification status failed. try to submit
                try:
                    notification_status = self._indexer.request_indexing(url)
                    self._num_submitted += 1
                    utils.logger.info(
                        "✅ Submitted for indexing. Should be indexed in "
                        "few days."
                    )
                except Exception:
                    utils.logger.error(f"Failed to submit {url}")
            if notification_status is not None:
                current_state.update(notification_status)
                # just setting dummy cache for debugging purpose. Cache is not
                # used if self._use_cache is False
                self._cache[url] = current_state
            if self._num_submitted > self.REQUEST_QUOTA:
                utils.logger.warning(
                    f"Daily request quota of {self.REQUEST_QUOTA} URLs is "
                    "exhausted! Try running this in a day"
                )

    def _collect_urls_for_submission(self) -> typing.List[str]:
        urls_to_submit: typing.List[str] = []
        for status in self._status_urls_map:
            if self._indexer.is_indexable(status):
                urls_to_submit.extend(self._status_urls_map[status])
        return urls_to_submit

    async def _check_indexing_status_batch(self, urls: typing.List[str]):
        tasks = [self._indexer.get_indexing_status(url) for url in urls]
        return await asyncio.gather(*tasks)

    def _check_indexing_status(self):
        utils.logger.info("Checking indexing status...")
        to_recheck: typing.List[str] = []
        for url in self._urls:
            current_state = self._cache.get(url) or {}
            if self._should_check_indexing_status(current_state):
                to_recheck.append(url)
            else:
                status = current_state.get("status")
                self._status_urls_map.setdefault(status, []).append(url)
        if to_recheck:
            self._batched_check_indexing_status(to_recheck)
        if self._use_cache:
            self._cache.dump()

    def _batched_check_indexing_status(
        self, urls: typing.List[str], batch_size: int = 10
    ):
        for url_batch in itertools.zip_longest(*[iter(urls)] * batch_size):
            url_batch = list(filter(None, url_batch))
            current_states = asyncio.run(
                self._check_indexing_status_batch(url_batch)
            )
            for url, state in zip(url_batch, current_states):
                current_state = self._cache.get(url) or {}
                current_state.update(state)
                self._cache[url] = current_state
                status = state.get("status")
                self._status_urls_map.setdefault(status, []).append(url)

    def _load_sitemaps(self):
        self._sitemaps = gsc.get_sitemaps(self._site_url, self._access_token)

    def _load_urls(self):
        for sitemap_url in self._sitemaps:
            parser = parse.SitemapParser(sitemap_url)
            for urls in parser.get_urls():
                self._urls.extend(urls)

    def _load_cached_urls(self):
        assert self._cache is not None, "Cache is required"
        self._urls = self._cache.keys()

    def _should_check_indexing_status(self, state: dict) -> bool:
        if not self._use_cache:
            return True
        # url not present in the cache
        if not state:
            return True
        index_status = state.get("status")
        should_index = self._indexer.is_indexable(index_status)
        last_checked = state.get("last_checked")

        if last_checked is None:
            stale = True
        else:
            stale = (
                datetime.datetime.utcnow() - last_checked > self._cache_timeout
            )
        return should_index or stale
