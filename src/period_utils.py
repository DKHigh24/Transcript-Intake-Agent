"""
period_utils.py
Derives the reporting period (meeting date, ISO week, calendar month) for a
transcript and provides path + slug helpers used by the weekly/monthly trend system.

Meeting date is parsed from the transcript filename (e.g. "... 6_3_2026.docx" ->
2026-06-03). Falls back to the file's last-modified date when no date is found.
An explicit override date may also be supplied.
"""

import re
from datetime import date, datetime
from pathlib import Path

OUTPUT_DIR = Path("output")
WEEKS_DIR = OUTPUT_DIR / "weeks"
HISTORY_DIR = OUTPUT_DIR / "history"
REPORTS_DIR = OUTPUT_DIR / "reports"
PRESENTATIONS_DIR = OUTPUT_DIR / "meeting_presentations"
HISTORY_PATH = HISTORY_DIR / "opportunities.json"

# Matches dates like 6_3_2026, 06-03-2026, 6.3.2026, 2026-06-03
_DATE_PATTERNS = [
    re.compile(r"(?P<y>\d{4})[._-](?P<m>\d{1,2})[._-](?P<d>\d{1,2})"),   # YYYY-M-D
    re.compile(r"(?P<m>\d{1,2})[._-](?P<d>\d{1,2})[._-](?P<y>\d{4})"),   # M-D-YYYY
    re.compile(r"(?P<m>\d{1,2})[._-](?P<d>\d{1,2})[._-](?P<y>\d{2})\b"), # M-D-YY
]


def parse_date_from_filename(filename: str) -> date | None:
    """Parse a meeting date out of a transcript filename. Returns None if absent."""
    stem = Path(filename).stem
    for pat in _DATE_PATTERNS:
        m = pat.search(stem)
        if not m:
            continue
        try:
            y = int(m.group("y"))
            if y < 100:
                y += 2000
            return date(y, int(m.group("m")), int(m.group("d")))
        except (ValueError, KeyError):
            continue
    return None


def resolve_meeting_date(input_path: str, override: str | None = None) -> date:
    """
    Resolve the meeting date for a transcript.

    Priority: explicit override (YYYY-MM-DD) > filename date > file mtime > today.
    """
    if override:
        return datetime.strptime(override, "%Y-%m-%d").date()

    parsed = parse_date_from_filename(input_path)
    if parsed:
        return parsed

    p = Path(input_path)
    if p.exists():
        return datetime.fromtimestamp(p.stat().st_mtime).date()

    return date.today()


def iso_week_label(d: date) -> str:
    """ISO week label, e.g. '2026-W23'."""
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def month_label(d: date) -> str:
    """Calendar month label, e.g. '2026-06'."""
    return f"{d.year}-{d.month:02d}"


def date_label(d: date) -> str:
    """ISO date label, e.g. '2026-06-03'."""
    return d.isoformat()


def period_info(d: date) -> dict:
    """Bundle of period labels for a given meeting date."""
    return {
        "date": date_label(d),
        "week": iso_week_label(d),
        "month": month_label(d),
    }


def week_archive_dir(d: date) -> Path:
    """Directory where a given week's artifacts are archived."""
    return WEEKS_DIR / date_label(d)


def monthly_report_path(month: str) -> Path:
    """Path for a monthly report HTML file, e.g. output/reports/monthly_2026-06.html."""
    return REPORTS_DIR / f"monthly_{month}.html"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase, hyphenated, alphanumeric slug used as a stable opportunity key."""
    slug = _SLUG_RE.sub("-", (text or "").lower()).strip("-")
    return slug or "untitled"


def ensure_dirs() -> None:
    """Create the persistent output directories if they do not exist."""
    for d in (WEEKS_DIR, HISTORY_DIR, REPORTS_DIR, PRESENTATIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)
