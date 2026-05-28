import re
from typing import Optional


def ms_to_str(ms: int) -> str:
    """3723456 → '1:02:03.456'  |  123456 → '2:03.456'"""
    h, rem = divmod(abs(ms), 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms_ = divmod(rem, 1_000)
    if h:
        return f"{h}:{m:02}:{s:02}.{ms_:03}"
    return f"{m}:{s:02}.{ms_:03}"


def str_to_ms(s: str) -> Optional[int]:
    """'1:02:03.456' → 3723456  |  '2:03.456' → 123456  |  formato errato → None"""
    m = re.fullmatch(r'(?:(\d+):)?(\d{1,2}):(\d{2})\.(\d{3})', s.strip())
    if not m:
        return None
    h, mi, sec, ms_ = (int(x or 0) for x in m.groups())
    return h * 3_600_000 + mi * 60_000 + sec * 1_000 + ms_
