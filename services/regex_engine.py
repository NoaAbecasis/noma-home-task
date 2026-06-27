import re

from api.models import PatternMatch


def apply_patterns(content: str, patterns: list[str]) -> list[PatternMatch]:
    results = []
    for pattern in patterns:
        compiled = re.compile(pattern, re.MULTILINE)
        matches = [m.group(0) for m in compiled.finditer(content)]
        results.append(PatternMatch(pattern=pattern, matches=matches))
    return results
