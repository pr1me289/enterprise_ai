"""Per-field assertion reporter.

Given an output dict and an ExpectationSet, evaluate every expectation
independently, log each field's pass/fail line, and raise ``AssertionError``
only at the end with a full summary. This preserves test failure localization
while giving humans (and CI logs) a full picture of what the model got right
versus wrong on every run.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from typing import Any

from tests.support.expected_outputs import ExpectationSet, FieldExpectation

logger = logging.getLogger("tests.field_reporter")


@dataclass(frozen=True)
class FieldResult:
    path: str
    description: str
    passed: bool
    observed: Any
    reason: str


# ---------------------------------------------------------------------------
# Dotted-path lookup supporting list indexing
# ---------------------------------------------------------------------------


_MISSING = object()


def _dotted_get(output: dict[str, Any], path: str) -> Any:
    cursor: Any = output
    for segment in path.split("."):
        if cursor is None:
            return _MISSING
        if isinstance(cursor, list):
            try:
                cursor = cursor[int(segment)]
                continue
            except (ValueError, IndexError):
                return _MISSING
        if isinstance(cursor, dict):
            if segment not in cursor:
                return _MISSING
            cursor = cursor[segment]
            continue
        return _MISSING
    return cursor


# ---------------------------------------------------------------------------
# Core evaluator
# ---------------------------------------------------------------------------


def _evaluate_one(output: dict[str, Any], exp: FieldExpectation) -> FieldResult:
    observed = _dotted_get(output, exp.path)
    if observed is _MISSING:
        if exp.optional:
            return FieldResult(
                path=exp.path,
                description=exp.description,
                passed=True,
                observed=None,
                reason="optional field not present — accepted",
            )
        return FieldResult(
            path=exp.path,
            description=exp.description,
            passed=False,
            observed=None,
            reason="field missing from output",
        )

    # Rule precedence: one_of > non_empty > empty > predicate > equals.
    # Exactly one mode should be set per FieldExpectation.
    if exp.one_of is not None:
        if observed in exp.one_of:
            return FieldResult(exp.path, exp.description, True, observed, f"one_of {exp.one_of!r}")
        return FieldResult(exp.path, exp.description, False, observed, f"expected one_of {exp.one_of!r}, got {observed!r}")

    if exp.non_empty:
        ok = bool(observed)
        return FieldResult(
            path=exp.path,
            description=exp.description,
            passed=ok,
            observed=observed,
            reason="non-empty" if ok else "expected non-empty, got empty/falsy",
        )

    if exp.empty:
        ok = observed == [] or observed == {} or observed == ""
        return FieldResult(
            path=exp.path,
            description=exp.description,
            passed=ok,
            observed=observed,
            reason="empty" if ok else f"expected empty, got {observed!r}",
        )

    if exp.predicate is not None:
        try:
            ok = bool(exp.predicate(observed))
        except Exception as exc:  # noqa: BLE001
            return FieldResult(
                path=exp.path,
                description=exp.description,
                passed=False,
                observed=observed,
                reason=f"predicate raised {type(exc).__name__}: {exc}",
            )
        return FieldResult(
            path=exp.path,
            description=exp.description,
            passed=ok,
            observed=observed,
            reason="predicate satisfied" if ok else "predicate failed",
        )

    # Fallback: equality. Covers all primitive-value expectations including
    # equals=False and equals=None.
    if observed == exp.equals:
        return FieldResult(exp.path, exp.description, True, observed, f"equals {exp.equals!r}")
    return FieldResult(exp.path, exp.description, False, observed, f"expected {exp.equals!r} got {observed!r}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_expectations(
    *,
    output: dict[str, Any],
    expectation_set: ExpectationSet,
    pipeline_run_id: str,
    extra_context: dict[str, Any] | None = None,
    monitor: Any | None = None,
) -> tuple[list[FieldResult], str]:
    """Evaluate every expectation, print per-field report, return (results, summary).

    If ``monitor`` is provided, each field's verdict is also forwarded as a
    ``FIELD_VERDICT`` event so the live console shows every ground-truth
    assertion as it happens (and the session-end totals count it).
    """
    results = [_evaluate_one(output, exp) for exp in expectation_set.expectations]
    passed_count = sum(1 for r in results if r.passed)
    total = len(results)

    header = (
        f"\n=== Field-by-field report ===\n"
        f"scenario={expectation_set.scenario} agent={expectation_set.agent} "
        f"step={expectation_set.step} pipeline_run_id={pipeline_run_id}\n"
    )
    if extra_context:
        header += "context=" + json.dumps(extra_context, default=str) + "\n"

    lines = [header]
    for r in results:
        flag = "PASS" if r.passed else "FAIL"
        preview = _truncate(r.observed)
        lines.append(f"  [{flag}] {r.path:<40} {r.description:<35} observed={preview} :: {r.reason}")
        if monitor is not None:
            monitor.field_verdict(
                path=r.path,
                description=r.description,
                passed=r.passed,
                observed=r.observed,
                reason=r.reason,
            )

    summary = f"\n  summary: {passed_count}/{total} fields passed"
    lines.append(summary)
    body = "\n".join(lines)
    # Print to stdout so pytest -s captures it; also log at INFO level.
    print(body, file=sys.stdout)
    logger.info(body)
    return results, body


def assert_all_passed(results: list[FieldResult]) -> None:
    """Raise AssertionError listing every failed field — never just the first."""
    failed = [r for r in results if not r.passed]
    if not failed:
        return
    lines = [f"{len(failed)} field expectation(s) failed:"]
    for r in failed:
        lines.append(f"  - {r.path}: {r.reason} (observed={_truncate(r.observed)!s})")
    raise AssertionError("\n".join(lines))


def _truncate(value: Any, limit: int = 120) -> str:
    try:
        rendered = json.dumps(value, default=str)
    except TypeError:
        rendered = repr(value)
    if len(rendered) > limit:
        return rendered[: limit - 3] + "..."
    return rendered
