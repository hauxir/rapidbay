"""Synchronous client for the TMDB v3 API."""

from typing import Any

import requests


class TMDBClient:
    """Make uncached requests to TMDB using an API key."""

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

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

        try:
            response = requests.get(f"{self.BASE_URL}{endpoint}", **request_kwargs)
            if response.status_code != 200:
                return None

            data = response.json()
            if isinstance(data, dict):
                return data
            return None
        except Exception:
            # Network failures and invalid JSON should not interrupt search results.
            return None

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
