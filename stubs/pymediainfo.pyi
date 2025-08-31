# Type stub for pymediainfo to resolve basedpyright errors


class Track:
    track_type: str | None
    streamorder: int | None
    language: str | None
    codec_id_info: str | None
    format: str | None
    duration: float | None


class MediaInfo:
    tracks: list[Track]

    @staticmethod
    def parse(filepath: str) -> MediaInfo: ...
