import datetime
import typing
from urllib.parse import urlparse

from . import gsc, parse, utils


class BulkIndexer:
    """Submits the URLs of a website for indexing in Google Search Console"""

    REQUEST_QUOTA = 200

    def __init__(
        self,
        access_token: str,
        domain: str = None,
        sitemap_url: str = None,
        use_cached_urls: bool = False,
    ) -> None:
        if domain is None and sitemap_url is None:
            raise ValueError("Either domain or sitemap URL is required")

        self._access_token = access_token
        self._sitemap_url = sitemap_url
        self._use_cached_urls = use_cached_urls
        if domain is not None:
            self._domain = domain
        else:
            self._domain = urlparse(sitemap_url).netloc
        self._site_url = gsc.get_site_url(self._domain)
        self._sitemaps = []
        self._urls = []
        self._cache = utils.StatusCache(self._site_url)
        self._indexer = gsc.Indexer(self._access_token, self._site_url)
        self._cache_timeout = datetime.timedelta(days=14)
        self._status_urls_map = {}
        self._num_submitted = 0

    def index(self):
        self._load_sitemaps()
        if not self._sitemaps:
            utils.logger.warning(
                f"❌ No sitemaps found for {self._domain}. Exiting..."
            )
            return
        # load cache
        self._cache.load()

        # get page urls
        if self._use_cached_urls:
            self._load_cached_urls()
        else:
            self._load_urls()
        if not self._urls:
            utils.logger.warning(
                f"❌ No URLs found for {self._domain}. Exiting..."
            )
            return
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
            return
        utils.logger.info(f"🔍 Found {num_urls} URLs for submission.")
        self._request_indexing(urls)
        utils.logger.info(
            "🚀 All done. Run this when you add new pages or update page "
            "content"
        )

    def _request_indexing(self, urls: typing.List[str]):
        for url in urls:
            utils.logger.info(f"👩‍💻 Working on {url}")
            current_state = self._cache[url] or {}
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
                # getting notification failed. try to submit
                try:
                    notification_status = self._indexer.request_indexing(url)
                    self._num_submitted += 1
                    utils.logger.info(
                        "✅ Submitted for indexing. Should be indexed few days."
                    )
                except Exception:
                    utils.logger.error(f"Failed to submit {url}")
            if notification_status is not None:
                current_state.update(notification_status)
                self._cache[url] = current_state
            if self._num_submitted > self.REQUEST_QUOTA:
                utils.logger.warning(
                    f"Daily request quota of {self.REQUEST_QUOTA} is "
                    "exhausted! Try running this in a day"
                )

    def _collect_urls_for_submission(self) -> typing.List[str]:
        urls_to_submit: typing.List[str] = []
        for status in self._status_urls_map:
            if self._indexer.is_indexable(status):
                urls_to_submit.extend(self._status_urls_map[status])
        return urls_to_submit

    def _check_indexing_status(self):
        # TODO: do async requests to speed things up.
        utils.logger.info("Checking indexing status...")
        for url in self._urls:
            current_state = self._cache[url] or {}
            if self._should_check_indexing_status(current_state):
                indexing_status = self._indexer.get_indexing_status(url)
                current_state.update(indexing_status)
                self._cache[url] = current_state
                status = indexing_status.get("status")
            else:
                status = current_state.get("status")
            self._status_urls_map.setdefault(status, []).append(url)

        self._cache.dump()

    def _load_sitemaps(self):
        if self._sitemap_url is not None:
            self._sitemaps = [self._sitemap_url]
        else:
            self._sitemaps = gsc.get_sitemaps(
                self._site_url, self._access_token
            )

    def _load_urls(self):
        for sitemap_url in self._sitemaps:
            parser = parse.SitemapParser(sitemap_url)
            for urls in parser.get_urls():
                self._urls.extend(urls)

    def _load_cached_urls(self):
        self._urls = self._cache.keys()

    def _should_check_indexing_status(self, state: dict) -> bool:
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