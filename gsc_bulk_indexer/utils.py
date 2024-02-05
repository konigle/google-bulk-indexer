import logging
import os
import pickle
import typing
import urllib.parse
from pprint import pp

from _collections_abc import dict_keys

logger = logging.getLogger("gsc_indexer")

__all__ = ["logger"]


class StatusCache(dict):
    """Simple cache to store the URL indexing status"""

    def __init__(self, site_url: str) -> None:
        self._site_url = site_url
        self._status = {}
        self._cache_file = self._get_cache_file_path()
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        logger.info(f"Loading cache entry for {self._site_url}")
        if os.path.exists(self._cache_file):
            with open(self._cache_file, "rb") as f:
                self._status = pickle.load(f)
                self._loaded = True
        else:
            logger.info("No cache entry found. Creating new cache entry...")

    def dump(self):
        logger.info(f"Saving cache entry for {self._site_url}")
        with open(self._cache_file, "wb") as f:
            pickle.dump(self._status, f)
        logger.info("Cache entry saved")

    def keys(self) -> dict_keys:
        return self._status.keys()

    def _get_cache_file_path(self):
        assert self._site_url is not None, "site_url is required"
        cache_dir = os.path.join(os.getcwd(), ".cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        filename = (
            self._site_url.replace("://", "_")
            .strip("/")
            .replace("/", "_")
            .replace(".", "_")
            .replace(":", "_")
            .replace("-", "_")
        )
        return os.path.join(cache_dir, f"{filename}.pkl")

    def __getitem__(self, __key: str) -> typing.Optional[dict]:
        return self._status.get(__key)

    def __setitem__(self, __key: str, __value: dict) -> None:
        self._status[__key] = __value

    def __str__(self) -> str:
        return self._status.__str__()

    def __bool__(self) -> bool:
        return bool(self._status)
