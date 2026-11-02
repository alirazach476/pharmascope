"""Reusable data-quality check framework."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pandas as pd

from pharmascope.validation.schemas import missing_required_columns
from pharmascope.validation.validation_results import (
    CheckResult,
    Severity,
    ValidationReport,
)


class DataQualityFramework:
    """Run severity-classified quality checks against a DataFrame."""

    def __init__(self, source: str, dataset: str) -> None:
        self.source = source
        self.dataset = dataset
        self._checks: list[CheckResult] = []

    def check_required_columns(
        self,
        df: pd.DataFrame,
        required: tuple[str, ...],
        *,
        severity: Severity = Severity.CRITICAL,
    ) -> CheckResult:
        missing = missing_required_columns(list(df.columns), required)
        result = CheckResult(
            source=self.source,
            dataset=self.dataset,
            check_name="required_columns",
            severity=severity,
            records_evaluated=len(df),
            failures_detected=len(missing),
            failure_percentage=(100.0 * len(missing) / max(len(required), 1)),
            recommended_action="Halt gold promotion; inspect upstream flattening."
            if missing
            else "None",
            details={"missing_columns": missing, "required": list(required)},
            passed=len(missing) == 0,
        )
        self._checks.append(result)
        return result

    def check_null_percentage(
        self,
        df: pd.DataFrame,
        column: str,
        *,
        max_null_pct: float = 50.0,
        severity: Severity = Severity.MEDIUM,
    ) -> CheckResult:
        if column not in df.columns:
            result = CheckResult(
                source=self.source,
                dataset=self.dataset,
                check_name=f"null_percentage:{column}",
                severity=Severity.HIGH,
                records_evaluated=len(df),
                failures_detected=1,
                failure_percentage=100.0,
                recommended_action=f"Column '{column}' missing; review schema.",
                passed=False,
            )
            self._checks.append(result)
            return result

        nulls = int(df[column].isna().sum() + (df[column] == "").sum())
        pct = 100.0 * nulls / max(len(df), 1)
        passed = pct <= max_null_pct
        result = CheckResult(
            source=self.source,
            dataset=self.dataset,
            check_name=f"null_percentage:{column}",
            severity=severity,
            records_evaluated=len(df),
            failures_detected=nulls,
            failure_percentage=pct,
            recommended_action="Investigate source missingness; do not impute silently."
            if not passed
            else "None",
            details={"max_null_pct": max_null_pct},
            passed=passed,
        )
        self._checks.append(result)
        return result

    def check_unique_keys(
        self,
        df: pd.DataFrame,
        keys: list[str],
        *,
        severity: Severity = Severity.CRITICAL,
    ) -> CheckResult:
        missing = [k for k in keys if k not in df.columns]
        if missing:
            result = CheckResult(
                source=self.source,
                dataset=self.dataset,
                check_name="unique_keys",
                severity=severity,
                records_evaluated=len(df),
                failures_detected=len(missing),
                failure_percentage=100.0,
                recommended_action=f"Missing key columns: {missing}",
                passed=False,
                details={"missing_keys": missing},
            )
            self._checks.append(result)
            return result

        dup_count = int(df.duplicated(subset=keys).sum())
        pct = 100.0 * dup_count / max(len(df), 1)
        result = CheckResult(
            source=self.source,
            dataset=self.dataset,
            check_name="unique_keys",
            severity=severity,
            records_evaluated=len(df),
            failures_detected=dup_count,
            failure_percentage=pct,
            recommended_action="Deduplicate before gold promotion." if dup_count else "None",
            details={"keys": keys},
            passed=dup_count == 0,
        )
        self._checks.append(result)
        return result

    def check_allowed_values(
        self,
        df: pd.DataFrame,
        column: str,
        allowed: set[Any],
        *,
        severity: Severity = Severity.HIGH,
    ) -> CheckResult:
        if column not in df.columns:
            result = CheckResult(
                source=self.source,
                dataset=self.dataset,
                check_name=f"allowed_values:{column}",
                severity=severity,
                records_evaluated=len(df),
                failures_detected=1,
                failure_percentage=100.0,
                recommended_action=f"Column '{column}' missing.",
                passed=False,
            )
            self._checks.append(result)
            return result

        series = df[column].dropna()
        invalid = series[~series.isin(allowed)]
        failures = int(len(invalid))
        pct = 100.0 * failures / max(len(df), 1)
        result = CheckResult(
            source=self.source,
            dataset=self.dataset,
            check_name=f"allowed_values:{column}",
            severity=severity,
            records_evaluated=len(df),
            failures_detected=failures,
            failure_percentage=pct,
            recommended_action="Quarantine unexpected categorical values."
            if failures
            else "None",
            details={
                "allowed": sorted(str(a) for a in allowed),
                "examples": invalid.astype(str).head(10).tolist(),
            },
            passed=failures == 0,
        )
        self._checks.append(result)
        return result

    def check_record_count_reconciliation(
        self,
        expected: int,
        actual: int,
        *,
        severity: Severity = Severity.HIGH,
        tolerance: int = 0,
    ) -> CheckResult:
        delta = abs(expected - actual)
        passed = delta <= tolerance
        result = CheckResult(
            source=self.source,
            dataset=self.dataset,
            check_name="record_count_reconciliation",
            severity=severity,
            records_evaluated=actual,
            failures_detected=0 if passed else 1,
            failure_percentage=0.0 if passed else 100.0,
            recommended_action="Investigate dropped or duplicated records."
            if not passed
            else "None",
            details={"expected": expected, "actual": actual, "tolerance": tolerance},
            passed=passed,
        )
        self._checks.append(result)
        return result

    def build_report(self) -> ValidationReport:
        return ValidationReport(
            report_id=str(uuid4()),
            source=self.source,
            dataset=self.dataset,
            checks=list(self._checks),
        )
