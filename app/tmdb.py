"""Synchronous client for the TMDB v3 API."""

import copy
from typing import Any

import requests

_CACHE_TTL_SECONDS = 6 * 60 * 60
_CACHE_MISS = object()
_disk_cache: Any = None


def tmdb_disk_cache() -> Any:
    """Shared on-disk cache for TMDB responses. Repeat searches skip the network."""
    global _disk_cache
    if _disk_cache is None:
        import os

        import diskcache
        import settings

        _disk_cache = diskcache.Cache(os.path.join(settings.CACHE_DIR, "tmdb"))
    return _disk_cache


class TMDBClient:
    """Make requests to TMDB using an API key.

    Pass a disk cache to reuse search and detail responses. Without one, every
    call goes to the network.
    """

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

    def __init__(self, api_key: str, cache: Any | None = None) -> None:
        self.api_key = api_key
        self._cache = cache

    def _auth(self) -> tuple[dict[str, str], dict[str, str]]:
        # TMDB v4 read tokens are JWTs and must be sent as a bearer token.
        # v3 API keys are sent as the api_key query parameter.
        if self.api_key.count(".") == 2:
            return {}, {"Authorization": f"Bearer {self.api_key}"}
        return {"api_key": self.api_key}, {}

    def _get_json(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any] | None:
        request_params, headers = self._auth()
        if params is not None:
            request_params.update(params)

        request_kwargs: dict[str, Any] = {"params": request_params, "timeout": 30}
        if headers:
            request_kwargs["headers"] = headers

        cache_key = (
            endpoint,
            tuple(sorted((key, value) for key, value in request_params.items() if key != "api_key")),
        )
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        try:
            response = requests.get(f"{self.BASE_URL}{endpoint}", **request_kwargs)
            if response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, dict):
                self._write_cache(cache_key, data)
                copied = copy.deepcopy(data)
                return copied if isinstance(copied, dict) else data
            return None
        except Exception:
            # Network failures and invalid JSON should not interrupt search results.
            return None

    def _read_cache(self, key: tuple[Any, ...]) -> dict[str, Any] | None:
        if self._cache is None:
            return None
        try:
            cached = self._cache.get(key, default=_CACHE_MISS)
        except Exception:
            return None
        if cached is _CACHE_MISS or not isinstance(cached, dict):
            return None
        copied = copy.deepcopy(cached)
        return copied if isinstance(copied, dict) else None

    def _write_cache(self, key: tuple[Any, ...], data: dict[str, Any]) -> None:
        if self._cache is None:
            return
        try:
            self._cache.set(key, data, expire=_CACHE_TTL_SECONDS)
        except Exception:
            return

    def search_multi(self, query: str) -> dict[str, Any] | None:
        """Search movies and TV shows matching a query."""
        return self._get_json("/search/multi", {"query": query})

    def get_tv_details(self, tv_id: int) -> dict[str, Any] | None:
        """Fetch details for a TV show by its TMDB ID."""
        return self._get_json(f"/tv/{tv_id}")

    def get_tv_season(self, tv_id: int, season_number: int) -> dict[str, Any] | None:
        """Fetch one season, including its episode list."""
        return self._get_json(f"/tv/{tv_id}/season/{season_number}")

    def get_movie_details(self, movie_id: int) -> dict[str, Any] | None:
        """Fetch details for a movie by its TMDB ID."""
        return self._get_json(f"/movie/{movie_id}")

    def get_image_url(self, path: str | None, size: str = "w185") -> str | None:
        """Build a TMDB image URL, or return None for an absent path."""
        if not path:
            return None
        return f"{self.IMAGE_BASE_URL}{size}{path}"
