import typing
import xml.etree.ElementTree

import requests

from . import utils


class SitemapParser:
    def __init__(self, sitemap_url: str, batch_size: int = 100):
        self.sitemap_url = sitemap_url
        self.batch_size = batch_size

    def fetch_sitemap(self, url: str):
        utils.logger.info(f"Fetching sitemap from {url}")

        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(
                f"Failed to fetch sitemap. Status code: {response.status_code}"
            )

    def parse_sitemap(
        self, sitemap_content: bytes
    ) -> typing.Generator[typing.List[str], None, None]:
        root = xml.etree.ElementTree.fromstring(sitemap_content)
        utils.logger.info("⚒️ Parsing sitemap to extract URLs...")

        if root.tag.endswith("sitemapindex"):
            for sitemap in root.findall(
                "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"
            ):
                sitemap_url = sitemap.find(
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                ).text
                sub_sitemap_content = self.fetch_sitemap(sitemap_url)
                yield from self.parse_sitemap(sub_sitemap_content)
        elif root.tag.endswith("urlset"):
            urls = []
            for url in root.findall(
                "{http://www.sitemaps.org/schemas/sitemap/0.9}url"
            ):
                loc = url.find(
                    "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                ).text
                urls.append(loc)
                if len(urls) == self.batch_size:
                    yield urls
                    urls = []
            if urls:
                yield urls

    def get_urls(self) -> typing.Generator[typing.List[str], None, None]:
        sitemap_content = self.fetch_sitemap(self.sitemap_url)
        yield from self.parse_sitemap(sitemap_content)


def get_sitemap_urls(
    sitemap_url: str, batch_size: int = 100
) -> typing.Generator[typing.List[str], None, None]:
    """Gets website URLs from a sitemap.

    Args:
        sitemap_url (str): URL of the sitemap
        batch_size (int, optional): Batch size for batching. Defaults to 100.

    Returns:
        typing.Generator[typing.List[str], None, None]: Generator of URL
            batches

    Yields:
        Iterator[typing.Generator[typing.List[str], None, None]]: URL batches
    """
    parser = SitemapParser(sitemap_url, batch_size)
    yield from parser.get_urls()
