# Type stub for iso639 to resolve basedpyright errors



class Language:
    part1: str
    part2b: str


class Languages:
    def get(self, part1: str = None, part2b: str = None) -> Language: ...


languages: Languages
