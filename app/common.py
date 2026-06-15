import os
import re
import threading
from typing import Any, Callable, Dict, Iterable, List, Pattern

import diskcache
import settings

# CJK, Hangul, Hiragana/Katakana, Cyrillic, Arabic, Hebrew, Thai, Devanagari ranges.
# Used by the trending filter to skip non-Latin-script titles.
_NON_LATIN_RE: Pattern[str] = re.compile(
    "["
    + "Ѐ-ԯ"        # Cyrillic + Cyrillic Supplement
    + "֐-׿"        # Hebrew
    + "؀-ۿ"        # Arabic
    + "ݐ-ݿ"        # Arabic Supplement
    + "ऀ-ॿ"        # Devanagari
    + "฀-๿"        # Thai
    + "　-ヿ"        # CJK Symbols and Punctuation, Hiragana, Katakana
    + "㐀-䶿"        # CJK Extension A
    + "一-鿿"        # CJK Unified Ideographs
    + "가-힯"        # Hangul Syllables
    + "豈-﫿"        # CJK Compatibility Ideographs
    + "＀-￯"        # Halfwidth and Fullwidth Forms
    + "]"
)
_blocklist_re: Pattern[str] | None = None


def _get_trending_title_blocklist_re() -> Pattern[str] | None:
    global _blocklist_re
    if _blocklist_re is None and settings.TRENDING_TITLE_BLOCKLIST:
        _blocklist_re = re.compile(
            "|".join(settings.TRENDING_TITLE_BLOCKLIST), re.IGNORECASE
        )
    return _blocklist_re


def should_drop_from_trending(title: str | None, categories: Iterable[int] | None) -> bool:
    """Filter applied only to the empty-search trending feed.

    Drops a result if any of:
      - one of its Newznab/Torznab category ids is in EXCLUDE_CATEGORIES_FROM_TRENDING
      - its title matches the TRENDING_TITLE_BLOCKLIST regex
      - TRENDING_BLOCK_NON_LATIN_TITLES is True and the title contains non-Latin script
    """
    if categories and settings.EXCLUDE_CATEGORIES_FROM_TRENDING:
        excluded = set(settings.EXCLUDE_CATEGORIES_FROM_TRENDING)
        for c in categories:
            if c in excluded:
                return True
    if not title:
        return False
    blocklist_re = _get_trending_title_blocklist_re()
    if blocklist_re is not None and blocklist_re.search(title):
        return True
    return bool(
        settings.TRENDING_BLOCK_NON_LATIN_TITLES and _NON_LATIN_RE.search(title)
    )


def threaded(fn: Callable[..., Any]) -> Callable[..., threading.Thread]:
    def wrapper(*args: Any, **kwargs: Any) -> threading.Thread:
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


def path_hierarchy(path: str) -> Dict[str, List[Any]] | List[Any] | str:
    hierarchy = os.path.basename(path)
    try:
        return {
            hierarchy: [
                path_hierarchy(os.path.join(path, contents))
                for contents in os.listdir(path)
            ]
        }
    except OSError:
        pass
    if hierarchy == "":
        return []
    return hierarchy


def normalize_filename(s: str) -> str:
    """Normalize filename to ASCII alphanumerics for matching, preserving path separators and periods."""
    return "".join(c for c in s if (c.isalnum() and c.isascii()) or c in "/\\.")


def memoize(expire: int = 300) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cache = diskcache.Cache(settings.CACHE_DIR)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Include the function identity in the key: all memoized functions
            # share the same cache directory, so e.g. jackett.search("x") and
            # prowlarr.search("x") would otherwise collide.
            key = (func.__module__, func.__qualname__, args, frozenset(kwargs.items()))
            if key in cache:
                return cache[key]
            result = func(*args, **kwargs)
            if result:
                cache.set(key, result, expire=expire)
            return result

        return wrapper
    return decorator
