"""Rule-based parsing of free-text eligibility criteria.

Pure Python (no Spark imports) so it can be unit tested directly and wrapped in
a UDF by :mod:`pda_data.transform`. The category names and numeric threshold
names are part of the Parquet contract consumed by ``pda-api``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Numeric thresholds: name -> (keyword regex, plausible min, plausible max)
THRESHOLDS: dict[str, tuple[str, float, float]] = {
    "hba1c": (r"hba1c|hb\s?a1c|a1c|glycosylated h|glycated h", 4.0, 15.0),
    "bmi": (r"\bbmi\b|body mass index", 14.0, 60.0),
    "fev1_pct": (r"fev\s?1(?!\s*/)", 10.0, 130.0),
    "pack_years": (r"pack[\s-]?years?", 1.0, 100.0),
    "egfr": (r"\begfr\b|glomerular filtration", 10.0, 120.0),
}

# Keyword categories: name -> regex. Order matters only for readability.
CATEGORIES: dict[str, str] = {
    "hba1c": THRESHOLDS["hba1c"][0],
    "bmi": THRESHOLDS["bmi"][0],
    "fev1": r"fev\s?1",
    "smoking_history": r"pack[\s-]?years?|smok",
    "renal": r"\begfr\b|glomerular filtration|renal|kidney|creatinine|dialysis",
    "exacerbation_history": r"exacerbation",
    "eosinophils": r"eosinophil",
    "cardiovascular": r"cardiovascular|myocardial|heart failure|cardiac|stroke|arrhythmia|angina|nyha",
    "hepatic": r"hepatic|liver|\balt\b|\bast\b|bilirubin|hepatitis",
    "pregnancy": r"pregnan|lactat|breast[\s-]?feed|nursing|childbearing|contracepti",
    "malignancy": r"malignan|cancer|carcinoma|neoplas",
    "infection": r"infection|tuberculosis|\bhiv\b|pneumonia",
    "substance_use": r"alcohol|drug abuse|substance abuse|illicit",
    "psychiatric": r"psychiatric|depression|suicid|cognitive impairment|dementia",
    "prior_therapy": (
        r"wash[\s-]?out|prior (?:treatment|therapy|use)|previous (?:treatment|therapy|use)|"
        r"biologic|monoclonal|stable dose|background therapy|within \d+ (?:days|weeks|months) (?:prior|before|of)"
    ),
    "insulin_use": r"insulin",
    "oxygen_therapy": r"oxygen therapy|supplemental oxygen|\bltot\b",
    "other_trial": r"investigational (?:drug|product|agent|device)|another (?:clinical )?(?:trial|study)",
    "hypersensitivity": r"hypersensitiv|allerg(?:y|ic) to|intoleran",
    "consent": r"informed consent|willing(?:ness)? (?:and able )?to",
}

_NUM = r"(\d{1,3}(?:[.,]\d{1,2})?)"
# A number followed by a time, volume or dose unit is not a threshold on the measure itself
# ("increase in FEV1 within 20 to 60 minutes"). Rates such as "60 mL/min" stay thresholds.
_NOT_A_UNIT = (
    r"(?![\d.,]*\d)(?!\s*(?:percent\s*)?(?:\(%\)\s*)?"
    r"(?:min(?:ute)?s?\b|hours?\b|hrs?\b|days?\b|weeks?\b|months?\b|"
    r"(?:m?l|millilit(?:er|re)s?)\b(?!\W*(?:\(ml\)\W*)?(?:per\s+)?(?:min|hour))|"
    r"mc?g\b(?!\s*/)|µg|puffs?\b|inhalations?\b))"
)
_HEADER = re.compile(r"^\W*(?:key\s+)?(inclusion|exclusion)\s+criteria\W*$", re.IGNORECASE)
_INLINE_HEADER = re.compile(r"(?:key\s+)?(inclusion|exclusion)\s+criteria\s*:?", re.IGNORECASE)
# A capitalised "Exclusion Criteria:" in the middle of a line starts a new section there.
_MIDLINE_HEADER = re.compile(r"(?<=\S)(?<!\bKey)[ \t]+(?=(?:Key\s+)?(?:Inclusion|Exclusion)\s+Criteria\s*:)")
# The registry escapes Markdown, so numbered items can arrive as "1\." or "2a.".
_BULLET = re.compile(r"^\s*(?:[*\-•·]|\(?\d{1,2}[a-z]?\\?[.)]|\(?[a-z]\\?[.)])\s+")
_REPLACEMENTS: list[tuple[str, str]] = [
    (r"\\", ""),
    (r"≥|=>|greater than or equal to|equal to or greater than|at least|no less than|not less than", ">="),
    (r"≤|=<|less than or equal to|equal to or less than|no more than|not more than|up to|at most", "<="),
    (r"greater than|more than|above|over|exceeding|higher than", ">"),
    (r"less than|below|under|lower than", "<"),
    (r"–|—|−", "-"),
]


@dataclass(frozen=True)
class Bounds:
    """Lower and upper bound of an allowed numeric window (either may be open)."""

    lower: float | None = None
    upper: float | None = None

    @property
    def empty(self) -> bool:
        return self.lower is None and self.upper is None


@dataclass
class ParsedCriteria:
    inclusion: list[str] = field(default_factory=list)
    exclusion: list[str] = field(default_factory=list)
    thresholds: dict[str, Bounds] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)


def normalise_text(text: str) -> str:
    """Lower-case and map verbal/unicode comparison operators to ASCII ones."""
    out = text.lower()
    for pattern, repl in _REPLACEMENTS:
        out = re.sub(pattern, repl, out)
    return out


def split_criteria(text: str | None) -> tuple[list[str], list[str]]:
    """Split an eligibility block into inclusion and exclusion items."""
    inclusion: list[str] = []
    exclusion: list[str] = []
    if not text:
        return inclusion, exclusion
    current = inclusion
    for raw_line in _MIDLINE_HEADER.sub("\n", text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        header = _HEADER.match(line)
        if header:
            current = inclusion if header.group(1).lower() == "inclusion" else exclusion
            continue
        inline = _INLINE_HEADER.match(line)
        if inline:
            current = inclusion if inline.group(1).lower() == "inclusion" else exclusion
            line = line[inline.end() :].strip()
            if not line:
                continue
        item = _BULLET.sub("", line).strip()
        if len(item) < 3:
            continue
        if _BULLET.match(raw_line) or not current:
            current.append(item)
        else:
            # Continuation of the previous item (wrapped line or sub-clause).
            current[-1] = f"{current[-1]} {item}"
    return inclusion, exclusion


def _to_float(value: str) -> float:
    return float(value.replace(",", "."))


def parse_bounds(
    segment: str, low: float, high: float, *, exclusion: bool = False, keyword: str | None = None
) -> Bounds:
    """Extract the allowed window from a normalised text segment.

    For exclusion criteria the stated window is what is *excluded*, so
    ``HbA1c > 10%`` in an exclusion list means an allowed upper bound of 10.
    ``keyword`` is the regex of the measure, needed to read a value written before it
    (``7.5% <= HbA1c <= 11%``).
    """

    def plausible(value: float) -> bool:
        return low <= value <= high

    lower: float | None = None
    upper: float | None = None
    rng = re.search(rf"{_NUM}\s*%?\s*(?:-|to|and)\s*(?:<=|<)?\s*{_NUM}{_NOT_A_UNIT}", segment)
    if rng and not exclusion:
        a, b = _to_float(rng.group(1)), _to_float(rng.group(2))
        if plausible(a) and plausible(b) and a < b:
            return Bounds(a, b)
    comparisons = re.findall(rf"(>=|<=|>|<)\s*(?:or\s*=\s*)?{_NUM}{_NOT_A_UNIT}", segment)
    if keyword:
        # "7.5% <= hba1c" states the same bound as "hba1c >= 7.5%".
        flipped = {">=": "<=", "<=": ">=", ">": "<", "<": ">"}
        value_first = re.findall(rf"{_NUM}\s*%?\s*(>=|<=|>|<)\s*(?:{keyword})", segment)
        comparisons = [(flipped[op], raw) for raw, op in value_first] + comparisons
    for op, raw in comparisons:
        value = _to_float(raw)
        if not plausible(value):
            continue
        is_lower = op.startswith(">")
        if exclusion:
            is_lower = not is_lower
        if is_lower and lower is None:
            lower = value
        elif not is_lower and upper is None:
            upper = value
    if lower is not None and upper is not None and lower >= upper:
        return Bounds()
    return Bounds(lower, upper)


def _merge(current: Bounds | None, new: Bounds) -> Bounds:
    """Every criterion has to hold, so the allowed window is the tightest of the stated ones.

    A window that would contradict the one already found is ignored.
    """
    if current is None:
        return new
    lowers = [value for value in (current.lower, new.lower) if value is not None]
    uppers = [value for value in (current.upper, new.upper) if value is not None]
    merged = Bounds(max(lowers, default=None), min(uppers, default=None))
    if merged.lower is not None and merged.upper is not None and merged.lower >= merged.upper:
        return current
    return merged


def item_thresholds(item: str, *, exclusion: bool) -> dict[str, Bounds]:
    """Numeric thresholds stated in a single criterion."""
    found: dict[str, Bounds] = {}
    text = normalise_text(item)
    for name, (keyword, low, high) in THRESHOLDS.items():
        match = re.search(keyword, text)
        if not match:
            continue
        # Look shortly before the keyword ("<= 10% HbA1c") and after it, up to the next clause.
        start = max(0, match.start() - 12)
        segment = re.split(r"[;]|\.\s", text[start : match.end() + 90])[0]
        bounds = parse_bounds(segment, low, high, exclusion=exclusion, keyword=keyword)
        if not bounds.empty:
            found[name] = bounds
    return found


def item_categories(item: str) -> list[str]:
    """Keyword categories a single criterion belongs to."""
    text = normalise_text(item)
    return [name for name, pattern in CATEGORIES.items() if re.search(pattern, text)]


def parse_eligibility(text: str | None) -> ParsedCriteria:
    """Parse a full eligibility block into items, thresholds and categories."""
    inclusion, exclusion = split_criteria(text)
    parsed = ParsedCriteria(inclusion=inclusion, exclusion=exclusion)
    categories: set[str] = set()
    for items, is_exclusion in ((inclusion, False), (exclusion, True)):
        for item in items:
            categories.update(item_categories(item))
            for name, bounds in item_thresholds(item, exclusion=is_exclusion).items():
                parsed.thresholds[name] = _merge(parsed.thresholds.get(name), bounds)
    parsed.categories = sorted(categories)
    return parsed


def parse_age_years(value: str | None) -> float | None:
    """Convert an API age string such as ``"18 Years"`` or ``"6 Months"`` to years."""
    if not value:
        return None
    match = re.match(r"\s*(\d+(?:\.\d+)?)\s*(year|month|week|day|hour|minute)", value.lower())
    if not match:
        return None
    amount = float(match.group(1))
    per_year = {"year": 1.0, "month": 12.0, "week": 52.18, "day": 365.25, "hour": 8766.0, "minute": 525960.0}
    return round(amount / per_year[match.group(2)], 2)


_STOP_RULES: list[tuple[str, str]] = [
    (
        "low_accrual",
        r"enrol|recruit|accrual|accru|unable to (?:find|identify) (?:patients|subjects|participants)|"
        r"lack of (?:eligible )?(?:patients|subjects|participants)|insufficient (?:patients|subjects|participants)",
    ),
    ("safety", r"safety|adverse|toxicit|side effect|benefit[\s:/-]*risk|risk[\s:/-]*benefit"),
    ("efficacy_futility", r"futil|efficacy|lack of effect|primary endpoint|interim analysis|no benefit"),
    ("funding", r"fund|financ|budget|grant"),
    ("business", r"business|sponsor|strategic|company|corporate|commercial|portfolio|administrative"),
]
# Mentions of recruitment that do not say it was too slow.
_NOT_LOW_ACCRUAL = re.compile(
    r"closed to (?:further )?(?:accrual|enrol\w*|recruit\w*)|"
    r"(?<!before )(?<!until )(?:accrual|enrol\w*|recruit\w*) (?:had been |has been |was |is |were )?complete\w*"
)
_NOT_SAFETY = re.compile(
    r"no(?:t|n)?[\s-]*(?:due to |related to |for |a )?(?:any )?safety|no safety|unrelated to safety|non-safety"
)


def classify_why_stopped(reason: str | None) -> str:
    """Bucket a free-text ``whyStopped`` reason. Returns ``"none"`` when empty."""
    if not reason or not reason.strip():
        return "none"
    text = _NOT_LOW_ACCRUAL.sub("", reason.lower())
    for category, pattern in _STOP_RULES:
        if category == "safety" and _NOT_SAFETY.search(text):
            stripped = _NOT_SAFETY.sub("", text)
            if not re.search(pattern, stripped):
                continue
        if re.search(pattern, text):
            return category
    return "other"
