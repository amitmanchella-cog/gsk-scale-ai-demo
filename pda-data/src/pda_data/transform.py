"""PySpark transforms: raw ClinicalTrials.gov API v2 studies -> per-trial features.

Cleaning rules (documented in the README):

* one row per trial: duplicates across indication queries are resolved in favour of
  the indication named in the trial's own condition list, then alphabetically;
* only interventional phase 2 / phase 3 trials (PHASE1/PHASE2 counts as phase group 2,
  PHASE2/PHASE3 as phase group 3);
* rows without an enrollment count, start date or primary completion date, or with a
  non-positive duration, are dropped;
* a missing site list is kept as ``site_count = null`` with a null accrual rate.
"""

from __future__ import annotations

from typing import Any

from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

from pda_data import criteria
from pda_data.schema import (
    ACCRUAL_BENCHMARK_COLUMNS,
    ACCRUAL_PERCENTILES,
    COUNTRY_ACCRUAL_COLUMNS,
    CRITERIA_SCHEMA,
    RECRUITING_COLUMNS,
    THRESHOLD_NAMES,
    TRIAL_FEATURE_COLUMNS,
)

INDICATION_KEYWORDS = {
    "asthma": "asthma",
    "copd": "copd|chronic obstructive|emphysema|chronic bronchitis",
    "type_2_diabetes": "type 2 diab|type ii diab|type2 diab|t2dm|niddm|non-insulin-dependent|diabetes mellitus, type 2",
}
DAYS_PER_MONTH = 30.4375


def _parse_criteria(text: str | None) -> dict[str, Any]:
    parsed = criteria.parse_eligibility(text)
    row: dict[str, Any] = {
        "n_inclusion": len(parsed.inclusion),
        "n_exclusion": len(parsed.exclusion),
        "categories": parsed.categories,
    }
    for name in THRESHOLD_NAMES:
        bounds = parsed.thresholds.get(name, criteria.Bounds())
        row[f"{name}_min"] = bounds.lower
        row[f"{name}_max"] = bounds.upper
    return row


parse_criteria_udf = F.udf(_parse_criteria, CRITERIA_SCHEMA)
parse_age_udf = F.udf(criteria.parse_age_years, T.DoubleType())
classify_stop_udf = F.udf(criteria.classify_why_stopped, T.StringType())


def _api_date(col: Column) -> Column:
    """API dates are ``YYYY-MM-DD`` or ``YYYY-MM``; month-only dates map to the 1st."""
    return F.coalesce(F.to_date(col, "yyyy-MM-dd"), F.to_date(F.concat(col, F.lit("-01")), "yyyy-MM-dd"))


def flatten(raw: DataFrame) -> DataFrame:
    """Flatten the nested API shape into typed, snake_case columns."""
    p = F.col("protocolSection")
    countries = F.transform(
        F.coalesce(p["contactsLocationsModule"]["locations"], F.array()), lambda loc: loc["country"]
    )
    countries = F.filter(countries, lambda c: c.isNotNull())
    phases = F.array_sort(F.coalesce(p["designModule"]["phases"], F.array()))
    return raw.select(
        F.col("queryIndication").alias("indication"),
        p["identificationModule"]["nctId"].alias("nct_id"),
        F.trim(p["identificationModule"]["briefTitle"]).alias("title"),
        F.upper(p["statusModule"]["overallStatus"]).alias("overall_status"),
        F.trim(p["statusModule"]["whyStopped"]).alias("why_stopped"),
        _api_date(p["statusModule"]["startDateStruct"]["date"]).alias("start_date"),
        _api_date(p["statusModule"]["primaryCompletionDateStruct"]["date"]).alias("primary_completion_date"),
        p["sponsorCollaboratorsModule"]["leadSponsor"]["class"].alias("sponsor_class"),
        F.coalesce(p["conditionsModule"]["conditions"], F.array()).alias("conditions"),
        F.upper(p["designModule"]["studyType"]).alias("study_type"),
        F.array_join(phases, "/").alias("phase"),
        F.when(F.array_contains(phases, "PHASE3"), F.lit(3))
        .when(F.array_contains(phases, "PHASE2"), F.lit(2))
        .alias("phase_group"),
        p["designModule"]["enrollmentInfo"]["count"].cast("int").alias("enrollment"),
        p["designModule"]["enrollmentInfo"]["type"].alias("enrollment_type"),
        p["eligibilityModule"]["eligibilityCriteria"].alias("eligibility_text"),
        p["eligibilityModule"]["healthyVolunteers"].alias("healthy_volunteers"),
        F.upper(p["eligibilityModule"]["sex"]).alias("sex"),
        p["eligibilityModule"]["minimumAge"].alias("minimum_age"),
        p["eligibilityModule"]["maximumAge"].alias("maximum_age"),
        countries.alias("site_countries"),
    )


def deduplicate(df: DataFrame) -> DataFrame:
    """Keep one row per trial, preferring the indication named in its conditions."""
    conditions = F.lower(F.array_join("conditions", " | "))
    matches = F.lit(1)
    for indication, pattern in INDICATION_KEYWORDS.items():
        matches = F.when((F.col("indication") == indication) & conditions.rlike(pattern), F.lit(0)).otherwise(matches)
    window = Window.partitionBy("nct_id").orderBy(matches, F.col("indication"))
    return df.withColumn("_rank", F.row_number().over(window)).filter("_rank = 1").drop("_rank")


def clean(df: DataFrame) -> DataFrame:
    """Apply the row-level cleaning rules."""
    return (
        df.filter(F.col("nct_id").isNotNull())
        .filter(F.col("study_type") == "INTERVENTIONAL")
        .filter(F.col("phase_group").isNotNull())
        .filter(F.col("indication").isin(*INDICATION_KEYWORDS))
    )


def add_site_features(df: DataFrame) -> DataFrame:
    sites = F.size("site_countries")
    return (
        df.withColumn("site_count", F.when(sites > 0, sites))
        .withColumn("countries", F.array_sort(F.array_distinct("site_countries")))
        .withColumn("country_count", F.size("countries"))
    )


def add_duration_and_accrual(df: DataFrame) -> DataFrame:
    """Duration (start to primary completion) and accrual rate per site per month."""
    months = F.round(F.datediff("primary_completion_date", "start_date") / F.lit(DAYS_PER_MONTH), 2)
    rate = F.col("enrollment") / (F.col("site_count") * F.col("duration_months"))
    return df.withColumn("duration_months", months).withColumn(
        "accrual_rate_per_site_month", F.round(F.when(F.col("site_count") > 0, rate), 4)
    )


def add_eligibility_features(df: DataFrame) -> DataFrame:
    parsed = parse_criteria_udf("eligibility_text")
    out = (
        df.withColumn("_criteria", parsed)
        .withColumn("min_age_years", parse_age_udf("minimum_age"))
        .withColumn("max_age_years", parse_age_udf("maximum_age"))
        .withColumn("n_inclusion", F.col("_criteria.n_inclusion"))
        .withColumn("n_exclusion", F.col("_criteria.n_exclusion"))
        .withColumn("criteria_categories", F.col("_criteria.categories"))
    )
    for name in THRESHOLD_NAMES:
        for side in ("min", "max"):
            out = out.withColumn(f"{name}_{side}", F.col(f"_criteria.{name}_{side}"))
    return out.drop("_criteria")


def add_termination_features(df: DataFrame) -> DataFrame:
    category = F.when(F.col("overall_status") == "TERMINATED", classify_stop_udf("why_stopped")).otherwise(
        F.lit("none")
    )
    return df.withColumn("stop_category", category).withColumn(
        "low_accrual_terminated",
        (F.col("overall_status") == "TERMINATED") & (F.col("stop_category") == "low_accrual"),
    )


def build_trial_features(raw: DataFrame) -> DataFrame:
    """Full transform for the completed/terminated benchmark: one row per trial."""
    df = clean(deduplicate(flatten(raw)))
    df = df.filter(F.col("overall_status").isin("COMPLETED", "TERMINATED"))
    df = df.filter(
        F.col("enrollment").isNotNull()
        & (F.col("enrollment") >= 0)
        & F.col("start_date").isNotNull()
        & F.col("primary_completion_date").isNotNull()
    )
    df = add_duration_and_accrual(add_site_features(df)).filter(F.col("duration_months") > 0)
    df = add_termination_features(add_eligibility_features(df))
    return df.select(*TRIAL_FEATURE_COLUMNS).orderBy("nct_id")


def build_recruiting_trials(raw: DataFrame) -> DataFrame:
    """Recruiting trials exploded to one row per trial and country (competition view)."""
    df = clean(deduplicate(flatten(raw))).filter(F.col("overall_status") == "RECRUITING")
    exploded = df.select("*", F.explode("site_countries").alias("country"))
    keys = [c for c in RECRUITING_COLUMNS if c != "sites_in_country"]
    return (
        exploded.groupBy(*keys)
        .agg(F.count(F.lit(1)).cast("int").alias("sites_in_country"))
        .select(*RECRUITING_COLUMNS)
        .orderBy("nct_id", "country")
    )


def _usable_rate() -> Column:
    """The accrual rate when it can feed a forecast: known and above zero."""
    rate = F.col("accrual_rate_per_site_month")
    return F.when(rate > 0, rate)


def _count_if(condition: Column) -> Column:
    return F.sum(F.when(condition, 1).otherwise(0)).cast("int")


def build_accrual_benchmarks(features: DataFrame) -> DataFrame:
    """Accrual-rate distribution and low-accrual termination share per indication and phase group.

    This is the distribution the enrollment forecast in ``pda-api`` falls back to when a
    protocol has too few similar trials with a usable rate. Percentiles are exact and
    computed only over trials with registered sites and a rate above zero.
    """
    rate = _usable_rate()
    percentiles = [F.percentile(rate, p / 100).alias(f"accrual_rate_p{p}") for p in ACCRUAL_PERCENTILES]
    return (
        features.groupBy("indication", "phase_group")
        .agg(
            F.count(F.lit(1)).cast("int").alias("n_trials"),
            F.count(rate).cast("int").alias("n_with_accrual_rate"),
            *percentiles,
            F.percentile("site_count", 0.5).alias("median_site_count"),
            F.percentile("duration_months", 0.5).alias("median_duration_months"),
            _count_if(F.col("overall_status") == "TERMINATED").alias("n_terminated"),
            _count_if(F.col("low_accrual_terminated")).alias("n_low_accrual_terminated"),
        )
        .withColumn("low_accrual_terminated_share", F.col("n_low_accrual_terminated") / F.col("n_trials"))
        .select(*ACCRUAL_BENCHMARK_COLUMNS)
        .orderBy("indication", "phase_group")
    )


def build_country_accrual(features: DataFrame) -> DataFrame:
    """Per indication, phase group and country: how trials with sites in that country accrued.

    A trial counts once for every country it had sites in. The rate is the trial-level rate
    (the registry does not publish enrollment per country), so this ranks countries by the
    trials that ran there rather than measuring the country alone.
    """
    rate = _usable_rate()
    return (
        features.select("*", F.explode("countries").alias("country"))
        .groupBy("indication", "phase_group", "country")
        .agg(
            F.count(F.lit(1)).cast("int").alias("n_trials"),
            F.count(rate).cast("int").alias("n_with_accrual_rate"),
            F.percentile(rate, 0.5).alias("accrual_rate_p50"),
            _count_if(F.col("low_accrual_terminated")).alias("n_low_accrual_terminated"),
        )
        .select(*COUNTRY_ACCRUAL_COLUMNS)
        .orderBy("indication", "phase_group", "country")
    )
