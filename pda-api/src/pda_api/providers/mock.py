"""Deterministic rule and regex based extraction. No model, no network."""

from __future__ import annotations

import re

from pda_api import criteria as cp
from pda_api.schemas import Criterion, PlannedCountry, Population, ProtocolDesign

INDICATIONS: dict[str, str] = {
    "type_2_diabetes": r"type\s*(?:2|ii)\s*diabet|\bt2dm?\b|non[- ]insulin[- ]dependent diabet",
    "copd": r"\bcopd\b|chronic obstructive pulmonary|chronic obstructive lung",
    "asthma": r"asthma",
}
# Canonical country name (as used by ClinicalTrials.gov) -> extra spellings.
COUNTRIES: dict[str, list[str]] = {
    "United States": ["United States of America", "USA", "U.S.A.", "U.S.", "US"],
    "United Kingdom": ["UK", "U.K.", "Great Britain"],
    "Germany": [],
    "France": [],
    "Spain": [],
    "Italy": [],
    "Poland": [],
    "Canada": [],
    "China": [],
    "Japan": [],
    "India": [],
    "Brazil": [],
    "Mexico": [],
    "Argentina": [],
    "Australia": [],
    "Netherlands": ["The Netherlands"],
    "Belgium": [],
    "Sweden": [],
    "Denmark": [],
    "Hungary": [],
    "Czechia": ["Czech Republic"],
    "Bulgaria": [],
    "Romania": [],
    "Ukraine": [],
    "Russian Federation": ["Russia"],
    "South Africa": [],
    "Korea, Republic of": ["South Korea", "Republic of Korea"],
    "Taiwan": [],
    "Israel": [],
    "Turkey": ["Türkiye"],
    "Egypt": [],
    "Thailand": [],
}
_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
_SITE = r"(?:study\s+|investigational\s+|clinical\s+|research\s+|trial\s+)?(?:sites?|cent(?:er|re)s?)"
_NUMBERING = re.compile(r"^\s*(?:section\s+)?\d+(?:\.\d+)*[.):]?\s+", re.IGNORECASE)
_CRITERIA_HEADING = re.compile(r"(?:key\s+)?(inclusion|exclusion)\s+criteria", re.IGNORECASE)
_LABEL_LINE = re.compile(r"^[A-Z][A-Za-z /&()-]{2,40}:(?:\s|$)")
_PHASE = re.compile(r"phase\s*:?\s*(2\s*/\s*3|ii\s*/\s*iii|iii|ii|3|2)[ab]?\b", re.IGNORECASE)
_AGE_HINT = re.compile(r"\bage[ds]?\b|years? old|years of age|year-old")
_ENROLLMENT_PATTERNS = [
    r"(?:planned|target|total|anticipated)\s+(?:enrol+ment|sample size|number of (?:participants|patients|subjects))"
    r"[^\d\n]{0,60}?(\d[\d,]*)",
    r"(?:approximately|about|total of|up to)\s+(\d[\d,]*)\s+(?:eligible\s+)?(?:participants|patients|subjects|adults)",
    r"(\d[\d,]*)\s+(?:participants|patients|subjects)\s+(?:will be|are to be|to be)\s+(?:randomi[sz]ed|enrol+ed)",
    r"(?:enrol+|randomi[sz]e)\s+(\d[\d,]*)\s+(?:participants|patients|subjects)",
]


def _is_heading(line: str) -> bool:
    stripped = _NUMBERING.sub("", line).strip()
    letters = [char for char in stripped if char.isalpha()]
    all_caps = len(letters) >= 6 and all(char.isupper() for char in letters)
    return all_caps or bool(_LABEL_LINE.match(stripped))


def split_sections(text: str) -> tuple[str, str]:
    """Return (eligibility block, everything else).

    The eligibility block starts at the first inclusion/exclusion heading and ends
    at the next section heading (an all-caps line or a short ``Label:`` line).
    """
    eligibility: list[str] = []
    rest: list[str] = []
    inside = False
    for line in text.splitlines():
        stripped = _NUMBERING.sub("", line).strip()
        heading = _CRITERIA_HEADING.match(stripped)
        if heading and len(stripped) <= len(heading.group(0)) + 3:
            inside = True
            eligibility.append(f"{heading.group(1).capitalize()} Criteria:")
            continue
        if inside and line.strip() and _is_heading(line):
            inside = False
        (eligibility if inside else rest).append(line)
    return "\n".join(eligibility), "\n".join(rest)


def _label(text: str, names: str) -> str | None:
    match = re.search(rf"^\s*(?:\d+(?:\.\d+)*[.)]?\s+)?(?:{names})\s*[:\-]\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def extract_indication(title: str | None, body: str) -> str | None:
    for source in (_label(body, "indication|condition|disease|therapeutic area"), title):
        if source:
            for key, pattern in INDICATIONS.items():
                if re.search(pattern, source, re.IGNORECASE):
                    return key
    counts = {key: len(re.findall(pattern, body, re.IGNORECASE)) for key, pattern in INDICATIONS.items()}
    best = max(counts, key=lambda key: counts[key])
    return best if counts[best] else None


def extract_phase(title: str | None, body: str) -> tuple[str | None, int | None]:
    labelled = _label(body, "study phase|phase|development phase")
    for source in (f"phase {labelled}" if labelled else None, title, body):
        match = _PHASE.search(source) if source else None
        if match:
            token = re.sub(r"\s", "", match.group(1).lower())
            if "/" in token:
                return "PHASE2/PHASE3", 3
            return ("PHASE3", 3) if token in {"3", "iii"} else ("PHASE2", 2)
    return None, None


def extract_enrollment(body: str) -> int | None:
    for pattern in _ENROLLMENT_PATTERNS:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            value = int(match.group(1).replace(",", ""))
            if value > 0:
                return value
    return None


def extract_countries(body: str) -> list[PlannedCountry]:
    found: list[tuple[int, PlannedCountry]] = []
    for canonical, aliases in COUNTRIES.items():
        for spelling in sorted([canonical, *aliases], key=len, reverse=True):
            name = re.escape(spelling)
            match = re.search(rf"(?<![A-Za-z]){name}(?![A-Za-z])", body)
            if not match:
                continue
            after = re.match(rf"\s*[(:,\-]?\s*(\d+)\s*{_SITE}", body[match.end() :], re.IGNORECASE)
            before = re.search(rf"(\d+)\s*{_SITE}\s*(?:in|across)\s*(?:the\s*)?$", body[: match.start()], re.IGNORECASE)
            sites = int(after.group(1)) if after else int(before.group(1)) if before else None
            found.append((match.start(), PlannedCountry(country=canonical, sites=sites)))
            break
    return [country for _, country in sorted(found, key=lambda pair: pair[0])]


def extract_site_count(body: str, countries: list[PlannedCountry]) -> int | None:
    labelled = _label(body, "number of sites|total sites|planned sites|sites")
    if labelled and (match := re.match(r"(?:approximately\s+)?(\d+)", labelled)):
        return int(match.group(1))
    words = "|".join(_WORD_NUMBERS)
    total = re.search(
        rf"(\d+)\s+{_SITE}\s+(?:in|across)\s+(?:\d+|{words}|a single)\s+countr", body, re.IGNORECASE
    ) or re.search(rf"(?:at|across|total of)\s+(?:approximately\s+)?(\d+)\s+{_SITE}", body, re.IGNORECASE)
    if total:
        return int(total.group(1))
    if countries and all(country.sites for country in countries):
        return sum(country.sites or 0 for country in countries)
    return None


def parse_age(item: str, *, exclusion: bool = False) -> cp.Bounds:
    """Eligible age window stated in one criterion (empty if it is not about age)."""
    text = cp.normalise_text(item)
    if not _AGE_HINT.search(text):
        return cp.Bounds()
    rng = re.search(
        r"(\d{1,3})\s*(?:years?)?\s*(?:-|to|and)\s*(?:<=|<)?\s*(\d{1,3})\s*(?:years|yrs|\(|,|$|inclusive)", text
    )
    if rng and not exclusion:
        low, high = float(rng.group(1)), float(rng.group(2))
        if 0 <= low < high <= 120:
            return cp.Bounds(low, high)
    lower: float | None = None
    upper: float | None = None
    for op, raw in re.findall(r"(>=|<=|>|<)\s*(?:or\s*=\s*)?(\d{1,3})", text):
        value = float(raw)
        is_lower = op.startswith(">") != exclusion
        if is_lower and lower is None:
            lower = value
        elif not is_lower and upper is None:
            upper = value
    if lower is None and (
        m := re.search(r"(\d{1,3})\s*years?(?:\s*of age|\s*old)?\s*(?:or|and)\s*(?:older|>|more)", text)
    ):
        lower = float(m.group(1))
    if upper is None and (
        m := re.search(r"(\d{1,3})\s*years?(?:\s*of age|\s*old)?\s*(?:or|and)\s*(?:younger|<|less)", text)
    ):
        upper = float(m.group(1))
    if lower is not None and upper is not None and lower >= upper:
        return cp.Bounds()
    return cp.Bounds(lower, upper)


def build_criteria(eligibility: str) -> list[Criterion]:
    inclusion, exclusion = cp.split_criteria(eligibility)
    out: list[Criterion] = []
    for kind, prefix, items in (("inclusion", "I", inclusion), ("exclusion", "E", exclusion)):
        for index, item in enumerate(items, start=1):
            is_exclusion = kind == "exclusion"
            age = parse_age(item, exclusion=is_exclusion)
            thresholds = cp.item_thresholds(item, exclusion=is_exclusion)
            categories = sorted(
                (name for name in cp.item_categories(item) if name != "consent"),
                key=lambda name: name == "prior_therapy",  # the broadest category goes last
            )
            parameter: str | None = None
            bounds = cp.Bounds()
            if not age.empty and not thresholds:
                category, parameter, bounds = "age", "age", age
            elif thresholds:
                parameter, bounds = next(iter(thresholds.items()))
                category = parameter
            elif categories:
                category = categories[0]
            else:
                category = "consent" if cp.item_categories(item) else "other"
            out.append(
                Criterion(
                    id=f"{prefix}{index}",
                    kind=kind,  # type: ignore[arg-type]
                    text=item,
                    category=category,
                    parameter=parameter,
                    lower=bounds.lower,
                    upper=bounds.upper,
                )
            )
    return out


def build_population(criteria: list[Criterion], body: str, eligibility: str) -> Population:
    min_age = next((c.lower for c in criteria if c.parameter == "age" and c.lower is not None), None)
    max_age = next((c.upper for c in criteria if c.parameter == "age" and c.upper is not None), None)
    text = eligibility.lower()
    sex = "ALL"
    if re.search(r"\b(?:females?|women) only\b|\bpostmenopausal women\b", text):
        sex = "FEMALE"
    elif re.search(r"\b(?:males?|men) only\b", text):
        sex = "MALE"
    return Population(
        min_age=min_age,
        max_age=max_age,
        sex=sex,  # type: ignore[arg-type]
        healthy_volunteers=bool(re.search(r"healthy (?:volunteers|participants|subjects)", body.lower())),
        summary=_label(body, "study population|target population|population"),
    )


class MockProvider:
    """Stands in for a language model with deterministic rules."""

    name = "mock"

    def extract_design(self, text: str) -> ProtocolDesign:
        eligibility, body = split_sections(text)
        title = _label(body, "protocol title|study title|title")
        if not title:
            title = next((line.strip() for line in body.splitlines() if line.strip()), None)
        phase, phase_group = extract_phase(title, body)
        criteria = build_criteria(eligibility)
        countries = extract_countries(body)
        site_count = extract_site_count(body, countries)
        if site_count and len(countries) == 1 and countries[0].sites is None:
            countries[0].sites = site_count
        design = ProtocolDesign(
            title=title,
            indication=extract_indication(title, body),  # type: ignore[arg-type]
            phase=phase,
            phase_group=phase_group,
            population=build_population(criteria, body, eligibility),
            target_enrollment=extract_enrollment(body),
            planned_countries=countries,
            site_count=site_count,
            criteria=criteria,
        )
        missing = {
            "indication": design.indication,
            "phase": design.phase,
            "target enrollment": design.target_enrollment,
            "site count": design.site_count,
            "planned countries": design.planned_countries,
            "eligibility criteria": design.criteria,
        }
        design.warnings = [f"Could not extract {name}." for name, value in missing.items() if not value]
        return design
