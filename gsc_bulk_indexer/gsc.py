import datetime
import re
import typing
import urllib.parse

import aiohttp
import dateutil.parser
import requests

__all__ = [
    "get_site_url",
    "get_sitemaps",
    "Indexer",
]


def get_site_url(domain_or_url: str) -> str:
    if domain_or_url.startswith("http://") or domain_or_url.startswith(
        "https://"
    ):
        if domain_or_url.endswith("/"):
            return domain_or_url
        else:
            return domain_or_url + "/"
    else:
        return f"sc-domain:{domain_or_url}"


def get_sitemaps(site_url: str, access_token: str) -> typing.List[str]:
    headers = {"Authorization": f"Bearer {access_token}"}

    base_url = "https://www.googleapis.com/webmasters/v3/sites/"
    url = f"{base_url}{urllib.parse.quote_plus(site_url)}/sitemaps/"

    response = requests.get(url, headers=headers)
    if response.status_code == 403:
        raise PermissionError(
            "The service account does not have permission to access this site"
        )
    if response.status_code == 200:
        sitemaps = response.json()["sitemap"]
        return list(map(lambda sitemap: sitemap["path"], sitemaps))
    else:
        raise Exception(
            f"Failed to fetch sitemaps. Status code: {response.status_code}"
        )


class Indexer:
    BASE_API_URL = "https://indexing.googleapis.com/v3/urlNotifications"

    INDEXABLE_STATUSES = [
        "Discovered - currently not indexed",
        "Crawled - currently not indexed",
        "URL is unknown to Google",
        "Forbidden",
        "Error",
    ]

    def __init__(self, access_token: str, site_url: str) -> None:
        self._access_token = access_token
        self._site_url = site_url

    def request_indexing(self, url: str) -> dict:
        endpoint = ":publish"
        data = {"url": url, "type": "URL_UPDATED"}
        response = self._request(endpoint, "POST", data=data)
        if response.status_code == 200:
            return self._parse_notification_status(response.json())
        else:
            raise Exception(
                "Failed to request indexing. Status code: "
                f"{response.status_code}"
            )

    def remove_indexing(self, url: str) -> dict:
        endpoint = ":publish"
        data = {"url": url, "type": "URL_DELETED"}
        response = self._request(endpoint, "POST", data=data)
        if response.status_code == 200:
            return self._parse_notification_status(response.json())
        else:
            raise Exception(
                "Failed to remove indexing. Status code: "
                f"{response.status_code}"
            )

    def get_notification_status(self, url: str) -> dict:
        params = {"url": url}
        endpoint = "/metadata"
        response = self._request(endpoint, "GET", params=params)
        if response.status_code == 200:
            return self._parse_notification_status(response.json())
        else:
            raise Exception(
                "Failed to get status. Status code: " f"{response.status_code}"
            )

    async def get_indexing_status(self, inspection_url: str) -> dict:
        """Get indexing status of a URL

        Args:
            inspection_url (str): URL to inspect

        Returns:
            str: Indexing status
        """
        api = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"  # noqa
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "inspectionUrl": inspection_url,
            "siteUrl": self._site_url,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(api, headers=headers, json=data) as resp:
                if resp.status == 200:
                    resp_json = await resp.json()
                    resp_data = resp_json.get("inspectionResult", {}).get(
                        "indexStatusResult", {}
                    )
                    status = resp_data.get("coverageState", None)
                    last_crawled_at = None
                    if resp_data.get("lastCrawlTime"):
                        # not bothering with the timezone for now.
                        last_crawled_at = dateutil.parser.parse(
                            resp_data["lastCrawlTime"]
                        )
                    return {
                        "status": status,
                        "last_crawled_at": last_crawled_at,
                        "last_checked": datetime.datetime.utcnow(),
                    }
                elif resp.status == 403:
                    return {
                        "status": "Forbidden",
                        "last_crawled_at": None,
                    }
                else:
                    return {"status": "Error", "last_crawled_at": None}

    def is_indexable(self, status: str) -> bool:
        return status in self.INDEXABLE_STATUSES

    def _parse_notification_status(self, status: dict) -> dict:
        last_notified_at = None
        if status.get("latestUpdate") and status["latestUpdate"].get(
            "notifyTime"
        ):
            last_notified_at = dateutil.parser.parse(
                status["latestUpdate"]["notifyTime"]
            )
        elif status.get("latestRemove") and status["latestRemove"].get(
            "notifyTime"
        ):
            last_notified_at = dateutil.parser.parse(
                status["latestRemove"]["notifyTime"]
            )

        return {
            "last_notified_at": last_notified_at,
        }

    def _request(
        self,
        endpoint: str,
        method: str,
        params: dict = None,
        data: dict = None,
    ):
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        params = params or {}
        url = f"{self.BASE_API_URL}{endpoint}"
        response = requests.request(
            method, url, headers=headers, params=params, json=data
        )
        return response
