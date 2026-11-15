"""Explicit Spark schemas: the raw ClinicalTrials.gov API v2 shape and the output contract."""

from __future__ import annotations

from pyspark.sql import types as T


def _date_struct() -> T.StructType:
    return T.StructType([T.StructField("date", T.StringType())])


# Subset of the API v2 ``studies[]`` item that the pipeline reads. ``queryIndication``
# is added by ``scripts/fetch_snapshot.py`` to record which query returned the study.
RAW_SCHEMA = T.StructType(
    [
        T.StructField("queryIndication", T.StringType()),
        T.StructField(
            "protocolSection",
            T.StructType(
                [
                    T.StructField(
                        "identificationModule",
                        T.StructType(
                            [
                                T.StructField("nctId", T.StringType()),
                                T.StructField("briefTitle", T.StringType()),
                            ]
                        ),
                    ),
                    T.StructField(
                        "statusModule",
                        T.StructType(
                            [
                                T.StructField("overallStatus", T.StringType()),
                                T.StructField("whyStopped", T.StringType()),
                                T.StructField("startDateStruct", _date_struct()),
                                T.StructField("primaryCompletionDateStruct", _date_struct()),
                                T.StructField("completionDateStruct", _date_struct()),
                            ]
                        ),
                    ),
                    T.StructField(
                        "sponsorCollaboratorsModule",
                        T.StructType(
                            [T.StructField("leadSponsor", T.StructType([T.StructField("class", T.StringType())]))]
                        ),
                    ),
                    T.StructField(
                        "conditionsModule",
                        T.StructType([T.StructField("conditions", T.ArrayType(T.StringType()))]),
                    ),
                    T.StructField(
                        "designModule",
                        T.StructType(
                            [
                                T.StructField("studyType", T.StringType()),
                                T.StructField("phases", T.ArrayType(T.StringType())),
                                T.StructField(
                                    "enrollmentInfo",
                                    T.StructType(
                                        [
                                            T.StructField("count", T.LongType()),
                                            T.StructField("type", T.StringType()),
                                        ]
                                    ),
                                ),
                            ]
                        ),
                    ),
                    T.StructField(
                        "eligibilityModule",
                        T.StructType(
                            [
                                T.StructField("eligibilityCriteria", T.StringType()),
                                T.StructField("healthyVolunteers", T.BooleanType()),
                                T.StructField("sex", T.StringType()),
                                T.StructField("minimumAge", T.StringType()),
                                T.StructField("maximumAge", T.StringType()),
                            ]
                        ),
                    ),
                    T.StructField(
                        "contactsLocationsModule",
                        T.StructType(
                            [
                                T.StructField(
                                    "locations",
                                    T.ArrayType(T.StructType([T.StructField("country", T.StringType())])),
                                )
                            ]
                        ),
                    ),
                ]
            ),
        ),
    ]
)

THRESHOLD_NAMES = ["hba1c", "bmi", "fev1_pct", "pack_years", "egfr"]

CRITERIA_SCHEMA = T.StructType(
    [
        T.StructField("n_inclusion", T.IntegerType()),
        T.StructField("n_exclusion", T.IntegerType()),
        T.StructField("categories", T.ArrayType(T.StringType())),
        *[T.StructField(f"{name}_{side}", T.DoubleType()) for name in THRESHOLD_NAMES for side in ("min", "max")],
    ]
)

# Column order of ``trial_features`` (one row per trial). Consumed by pda-api.
TRIAL_FEATURE_COLUMNS = [
    "nct_id",
    "title",
    "indication",
    "phase",
    "phase_group",
    "overall_status",
    "why_stopped",
    "stop_category",
    "low_accrual_terminated",
    "sponsor_class",
    "start_date",
    "primary_completion_date",
    "duration_months",
    "enrollment",
    "enrollment_type",
    "site_count",
    "country_count",
    "countries",
    "accrual_rate_per_site_month",
    "sex",
    "healthy_volunteers",
    "min_age_years",
    "max_age_years",
    "n_inclusion",
    "n_exclusion",
    "criteria_categories",
    *[f"{name}_{side}" for name in THRESHOLD_NAMES for side in ("min", "max")],
]

# Column order of ``recruiting_trials`` (one row per recruiting trial and country).
RECRUITING_COLUMNS = [
    "nct_id",
    "title",
    "indication",
    "phase",
    "phase_group",
    "overall_status",
    "start_date",
    "enrollment",
    "country",
    "sites_in_country",
]

# Field-name fragments that must never appear in an output schema.
PERSON_LEVEL_TOKENS = ["name", "email", "phone", "contact", "investigator", "official", "birth", "dob", "patient_id"]
