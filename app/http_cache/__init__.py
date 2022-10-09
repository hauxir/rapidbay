from . import real_debrid


def get_cached_filelist(magnet_hash):
    cached_filelist = real_debrid.get_cached_filelist(magnet_hash)

    if cached_filelist:
        return cached_filelist

    return None


def get_cached_url(magnet_hash, filename):
    rd_cached_url = real_debrid.get_cached_url(magnet_hash, filename)

    if rd_cached_url:
        return rd_cached_url

    return None
