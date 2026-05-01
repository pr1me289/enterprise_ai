"""Build per-agent input bundles (structured_fields) from real scenario documents.

Two fixture strategies live side by side:

1. **Mock-pipeline capture** — run the real Supervisor with mock LLM adapters
   and capture ``supervisor.last_bundle_by_step`` after the run. This produces
   a bundle whose structured_fields are exactly what the BundleAssembler and
   retrieval router would pass to the real Anthropic adapter. We use this for
   Scenario 1 (happy path) because the pipeline runs cleanly through all six
   steps.

2. **Scenario-2 synthesis** — for the escalated scenario we cannot run the
   full pipeline because upstream ``escalated`` statuses halt the supervisor
   before STEP-04/05/06 execute. Instead we start from the Scenario 1 captured
   bundles (which have the right *shape*) and patch the upstream-output fields
   to Scenario 2 ground-truth values. The prompt sanctions this:

     > For downstream agent fixtures, use the expected output values from the
     > ground truth tables above as the upstream inputs — this makes fixtures
     > self-consistent without requiring a live prior-step run.

   For STEP-02 (which has no LLM upstream) we run a dedicated mock pipeline
   with the scenario_2 questionnaire so the captured bundle carries the real
   scenario_2 policy-chunk evidence.

The exposed callable is::

    build_bundles(scenario: Literal["scenario_1", "scenario_2"]) -> dict[str, dict]

which returns ``{agent_name: structured_fields_dict}`` keyed by the five domain
agent names used by ``agents.llm_caller``.
"""

from __future__ import annotations

import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from orchestration.mocks import ScenarioIndexedBackend, ScenarioLLMAdapter  # noqa: E402
from orchestration.models.enums import StepId  # noqa: E402
from orchestration.scenarios import complete_demo_scenario  # noqa: E402
from orchestration.supervisor import Supervisor  # noqa: E402

AGENT_BY_STEP: dict[str, str] = {
    "STEP-02": "it_security_agent",
    "STEP-03": "legal_agent",
    "STEP-04": "procurement_agent",
    "STEP-05": "checklist_assembler",
    "STEP-06": "checkoff_agent",
}


# ---------------------------------------------------------------------------
# Scenario-1 source: questionnaire + chunk directory
# ---------------------------------------------------------------------------


def _root_questionnaire() -> Path:
    """The canonical questionnaire that matches STEP-01's field_map schema.

    The scenarios_full_pipeline/scenario_1/source_mock_documents/OptiChain_VSQ_001_v2_1_scenario01.json copy
    uses a different top-level shape (submission_id, submission_timestamp) that
    does not satisfy STEP-01's required ``document_id`` / ``version`` fields,
    so we always start from the root file and layer scenario deltas through
    ``questionnaire_overrides``.
    """
    return REPO_ROOT / "mock_documents" / "OptiChain_VSQ_001_v2_1.json"


def _chunk_dir() -> Path:
    return REPO_ROOT / "data" / "processed" / "chunks"


# ---------------------------------------------------------------------------
# Scenario-2 ground-truth upstream outputs (from the testing prompt)
# ---------------------------------------------------------------------------


def _scenario_2_security_output() -> dict[str, Any]:
    return {
        "integration_type_normalized": "AMBIGUOUS",
        "integration_tier": "UNCLASSIFIED_PENDING_REVIEW",
        "data_classification": "REGULATED",
        "eu_personal_data_present": "YES",
        "fast_track_eligible": False,
        "fast_track_rationale": "DISALLOWED_AMBIGUOUS_SCOPE",
        "security_followup_required": True,
        "nda_status_from_questionnaire": "PENDING",
        "required_security_actions": [
            {
                "action_type": "SECURITY_REVIEW",
                "reason": "ERP integration tier remains unclassified pending architecture review.",
                "owner": "IT Security",
            }
        ],
        "policy_citations": [
            {
                "source_id": "ISP-001",
                "version": "4.2",
                "chunk_id": "ISP-001__section_12",
                "section_id": "12.2",
                "citation_class": "PRIMARY",
            }
        ],
        "status": "escalated",
    }


def _scenario_2_legal_output() -> dict[str, Any]:
    return {
        "dpa_required": True,
        "dpa_blocker": True,
        "nda_status": "PENDING",
        "nda_blocker": True,
        "trigger_rule_cited": [
            {"row_id": "A-01", "matrix_id": "DPA-TM-001", "version": "1.3"},
            {"row_id": "E-01", "matrix_id": "DPA-TM-001", "version": "1.3"},
        ],
        "policy_citations": [
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "chunk_id": "DPA-TM-001__row_A-01",
                "row_id": "A-01",
                "citation_class": "PRIMARY",
            }
        ],
        "status": "escalated",
    }


def _scenario_2_procurement_output() -> dict[str, Any]:
    return {
        "approval_path": "STANDARD",
        "fast_track_eligible": False,
        "required_approvals": [
            {"approver_role": "CISO", "status": "PENDING", "blocker": True},
            {"approver_role": "General Counsel", "status": "ESCALATED", "blocker": True},
            {"approver_role": "CPO", "status": "PENDING", "blocker": False},
            {"approver_role": "VP Operations", "status": "PENDING", "blocker": True},
            {"approver_role": "SVP Operations", "status": "PENDING", "blocker": True},
        ],
        "estimated_timeline": "Blocked pending DPA execution and ERP tier assignment",
        "policy_citations": [
            {
                "source_id": "PAM-001",
                "version": "2.0",
                "chunk_id": "PAM-001__row_A-T3",
                "row_id": "A-T3",
                "citation_class": "PRIMARY",
            }
        ],
        "status": "escalated",
    }


def _scenario_2_checklist_output() -> dict[str, Any]:
    """The STEP-05 output that the STEP-06 bundle should carry as finalized_checklist."""
    return {
        "pipeline_run_id": "SCENARIO_2_PIPELINE_RUN_ID",
        "vendor_name": "OptiChain, Inc.",
        "overall_status": "ESCALATED",
        "data_classification": "REGULATED",
        "fast_track_eligible": False,
        "approval_path": "STANDARD",
        "required_security_actions": _scenario_2_security_output()["required_security_actions"],
        "required_approvals": _scenario_2_procurement_output()["required_approvals"],
        "blockers": [
            {
                "blocker_type": "DPA_NOT_EXECUTED",
                "description": "GDPR Art. 28 DPA not executed; EU personal data in scope.",
                "resolution_owner": "General Counsel",
                "citation": {"source_id": "DPA-TM-001", "row_id": "A-01"},
            },
            {
                "blocker_type": "NDA_UNCONFIRMED",
                "description": "NDA draft transmitted 2024-02-19; not countersigned.",
                "resolution_owner": "Procurement / Legal",
                "citation": {"source_id": "ISP-001", "section_id": "12.1.4"},
            },
            {
                "blocker_type": "ERP_TIER_UNCLASSIFIED",
                "description": "ERP integration tier unassigned; pending architecture review.",
                "resolution_owner": "IT Security",
                "citation": {"source_id": "ISP-001", "section_id": "12.2"},
            },
        ],
    }


# ---------------------------------------------------------------------------
# Stakeholder map loader — used to enrich STEP-06 bundles for scenario_2
# ---------------------------------------------------------------------------


def _load_stakeholder_map(scenario: str) -> dict[str, Any]:
    import json

    base = REPO_ROOT / "scenarios_full_pipeline" / scenario / "source_mock_documents" / "Stakeholder_Map_PRQ_2024_0047.json"
    if not base.exists():
        base = REPO_ROOT / "mock_documents" / "Stakeholder_Map_PRQ_2024_0047.json"
    return json.loads(base.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Core: run the mock pipeline and capture bundles
# ---------------------------------------------------------------------------


def _run_mock_and_capture(*, questionnaire_path: Path, overrides: dict[str, Any] | None, agent_outputs: dict[str, dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """Run the Supervisor with a mock LLM adapter and capture structured_fields per step."""
    indexed_backend = ScenarioIndexedBackend(results=complete_demo_scenario().indexed_results)
    adapter_outputs = agent_outputs if agent_outputs is not None else complete_demo_scenario().agent_outputs
    supervisor = Supervisor(
        repo_root=REPO_ROOT,
        questionnaire_path=questionnaire_path,
        chunk_dir=_chunk_dir(),
        questionnaire_overrides=overrides or {},
        indexed_backend=indexed_backend,
        llm_adapter=ScenarioLLMAdapter(outputs=adapter_outputs),
    )
    supervisor.run()
    captured: dict[str, dict[str, Any]] = {}
    for step_id, ctx in supervisor.last_bundle_by_step.items():
        agent = AGENT_BY_STEP.get(step_id.value)
        if agent is None:
            continue
        captured[agent] = deepcopy(ctx.structured_fields)
    captured["_pipeline_run_id"] = supervisor.state.pipeline_run_id  # type: ignore[assignment]
    return captured


@lru_cache(maxsize=1)
def _scenario_1_captured() -> dict[str, dict[str, Any]]:
    """Scenario 1 captured bundles from a real mock pipeline run."""
    fx = complete_demo_scenario()
    return _run_mock_and_capture(
        questionnaire_path=_root_questionnaire(),
        overrides=fx.questionnaire_overrides,
        agent_outputs=fx.agent_outputs,
    )


# ---------------------------------------------------------------------------
# Scenario 2 synthesis
# ---------------------------------------------------------------------------


def scenario_escalated_step4_demo_questionnaire_overrides() -> dict[str, Any]:
    """Questionnaire deltas for the STEP-04 ESCALATED demo scenario.

    Identical regulated-non-fast-track profile to scenario_blocked_demo, but
    with vendor_class flipped to "Class F — Specialty Consulting Practice"
    (a vendor type the production PAM-001 v2.0 matrix does not cover).
    Bundle is admissible; PAM-001 retrieval succeeds; no retrieved row
    matches the Class F profile → Procurement Agent emits status=escalated.
    """
    return {
        "contract_details": {
            "vendor_class_assigned": "Class D — Technology Professional Services",
            "annual_contract_value_usd": 150000,
        },
        "product_and_integration": {
            "erp_integration": {
                "erp_type": "DIRECT_API",
                "integration_description": (
                    "Direct API integration to SAP S/4HANA. Vendor establishes "
                    "a persistent authenticated session via OAuth client "
                    "credentials and pulls production order, MRP, and inventory "
                    "data over the SAP OData API on a scheduled interval. No "
                    "middleware layer. No EU personal data in scope; US "
                    "manufacturing operational data only."
                ),
            }
        },
        "data_handling": {
            # Regulated profile but no EU personal data — override the canonical
            # EU-flavored regulated_data_types so the agent doesn't see a stale
            # EU mention alongside eu_personal_data_flag=false.
            "data_classification_self_reported": "REGULATED",
            "regulated_data_types": [
                "ERP transactional data (production orders, MRP outputs)",
                "Inventory position records",
            ],
            "personal_data_in_scope": False,
            "data_categories_in_scope": [
                "ERP transactional data (production orders, MRP outputs)",
                "Inventory position records",
                "Production scheduling data",
            ],
            "data_subjects": {
                "eu_personal_data_flag": False,
                "data_subjects_eu": False,
            },
        },
        "legal_and_contractual_status": {
            "existing_nda_status": "EXECUTED",
            "existing_dpa_status": "NOT_REQUIRED",
            "dpa_required": False,
        },
    }


def scenario_blocked_demo_questionnaire_overrides() -> dict[str, Any]:
    """Questionnaire deltas for the STEP-04 BLOCKED demo scenario.

    Profile: regulated enterprise vendor, direct API integration to SAP
    S/4HANA, no EU personal data, NDA executed, DPA not required. STEP-02
    yields REGULATED + non-fast-track; STEP-03 yields no DPA blocker; STEP-04
    blocks because PAM-001 is missing from the scenario's index registry.
    """
    return {
        "contract_details": {
            "vendor_class_assigned": "Class A — Enterprise Platform",
        },
        "product_and_integration": {
            "erp_integration": {
                "erp_type": "DIRECT_API",
                "integration_description": (
                    "Direct API integration to SAP S/4HANA. Vendor establishes "
                    "a persistent authenticated session via OAuth client "
                    "credentials and pulls production order, MRP, and inventory "
                    "data over the SAP OData API on a scheduled interval. No "
                    "middleware layer. No EU personal data in scope; US "
                    "manufacturing operational data only."
                ),
            }
        },
        "data_handling": {
            # Regulated profile but no EU personal data — override the canonical
            # EU-flavored regulated_data_types so the agent doesn't see a stale
            # EU mention alongside eu_personal_data_flag=false.
            "data_classification_self_reported": "REGULATED",
            "regulated_data_types": [
                "ERP transactional data (production orders, MRP outputs)",
                "Inventory position records",
            ],
            "personal_data_in_scope": False,
            "data_categories_in_scope": [
                "ERP transactional data (production orders, MRP outputs)",
                "Inventory position records",
                "Production scheduling data",
            ],
            "data_subjects": {
                "eu_personal_data_flag": False,
                "data_subjects_eu": False,
            },
        },
        "legal_and_contractual_status": {
            "existing_nda_status": "EXECUTED",
            "existing_dpa_status": "NOT_REQUIRED",
            "dpa_required": False,
        },
    }


def scenario_2_questionnaire_overrides() -> dict[str, Any]:
    """Questionnaire deltas that convert the root questionnaire into scenario_2.

    Used by both the mock STEP-02 bundle capture below and the live
    full-pipeline e2e test, which needs to drive the Supervisor off the
    same scenario_2 inputs.
    """
    return {
        "product_and_integration": {
            "erp_integration": {
                "erp_type": "DIRECT_API",
                "integration_description": (
                    "Direct API integration to SAP S/4HANA. Vendor establishes a "
                    "persistent authenticated session via OAuth client credentials "
                    "and pulls production order, MRP, and inventory data over the "
                    "SAP OData API on a scheduled interval. No middleware layer."
                ),
            }
        },
        "data_handling": {
            "personal_data_in_scope": True,
            "data_categories_in_scope": [
                "Shift schedules",
                "Employee IDs for EU-based facilities",
            ],
            "data_subjects": {
                "eu_personal_data_flag": True,
                "data_subjects_eu": True,
            },
        },
        "legal_and_contractual_status": {
            "existing_nda_status": "PENDING",
            "dpa_status": "NOT_STARTED",
            "dpa_required": True,
        },
    }


def _scenario_2_step02_bundle() -> dict[str, Any]:
    """Run the mock pipeline with scenario_2 questionnaire to capture a real STEP-02 bundle."""
    captured = _run_mock_and_capture(
        questionnaire_path=_root_questionnaire(),
        overrides=scenario_2_questionnaire_overrides(),
        agent_outputs=complete_demo_scenario().agent_outputs,
    )
    return captured["it_security_agent"]


@lru_cache(maxsize=1)
def _scenario_2_bundles() -> dict[str, dict[str, Any]]:
    """Return scenario-2 bundles, one per agent, built by patching scenario_1 baselines."""
    baseline = deepcopy(_scenario_1_captured())
    step02_bundle = _scenario_2_step02_bundle()

    sec_output = _scenario_2_security_output()
    legal_output = _scenario_2_legal_output()
    proc_output = _scenario_2_procurement_output()
    checklist_output = _scenario_2_checklist_output()
    stakeholder_map = _load_stakeholder_map("scenario_2")

    # STEP-02: real scenario-2 bundle captured above
    step02 = step02_bundle

    # STEP-03: patch upstream security_output, retain scenario-1 shaped DPA/NDA evidence.
    step03 = deepcopy(baseline["legal_agent"])
    step03["security_output"] = {
        "data_classification": sec_output["data_classification"],
        "status": sec_output["status"],
        "policy_citations": sec_output["policy_citations"],
    }
    step03["questionnaire"] = {
        "eu_personal_data_flag": True,
        "data_subjects_eu": True,
        "existing_nda_status": "PENDING",
    }

    # STEP-04: patch upstream outputs
    step04 = deepcopy(baseline["procurement_agent"])
    step04["it_security_output"] = sec_output
    step04["legal_output"] = legal_output

    # STEP-05: patch runtime_read upstream determinations
    step05 = deepcopy(baseline["checklist_assembler"])
    step05["it_security_agent"] = sec_output
    step05["legal_agent"] = legal_output
    step05["procurement_agent"] = proc_output

    # STEP-06: patch finalized_checklist, domain_outputs, and stakeholder_map
    step06 = deepcopy(baseline["checkoff_agent"])
    step06["finalized_checklist"] = checklist_output
    step06["domain_outputs"] = {
        "it_security_agent": sec_output,
        "legal_agent": legal_output,
        "procurement_agent": proc_output,
    }
    step06["stakeholder_map"] = stakeholder_map
    step06["escalations"] = [
        {
            "escalation_id": "ESC-002",
            "condition": "GDPR Art. 28 DPA not yet executed",
            "status": "ESCALATED",
            "resolution_owner": "General Counsel",
        }
    ]

    return {
        "it_security_agent": step02,
        "legal_agent": step03,
        "procurement_agent": step04,
        "checklist_assembler": step05,
        "checkoff_agent": step06,
        "_pipeline_run_id": "scenario_2_synthesized",  # type: ignore[dict-item]
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_bundles(scenario: str) -> dict[str, dict[str, Any]]:
    """Return ``{agent_name: structured_fields}`` for the named scenario.

    The returned dict also carries a ``_pipeline_run_id`` sentinel value — read
    that key to pass as ``pipeline_run_id`` to the ``call_*`` functions.
    """
    if scenario == "scenario_1":
        return deepcopy(_scenario_1_captured())
    if scenario == "scenario_2":
        validate_scenario_2_literals_against_spec()
        return deepcopy(_scenario_2_bundles())
    raise ValueError(f"unknown scenario: {scenario!r}")


# ---------------------------------------------------------------------------
# Drift validator — scenario_2 literals vs current agent output contracts
# ---------------------------------------------------------------------------


def validate_scenario_2_literals_against_spec() -> None:
    """Fail fast if a scenario_2 literal output drifted from the spec.

    The scenario_2 synthesis hardcodes upstream outputs as literal dicts so
    downstream agents can be tested in isolation of the halt condition.
    If the spec's required fields change and nobody updates these literals,
    downstream bundles silently carry a stale shape and the e2e test
    exercises something that diverges from the per-agent contract.

    This function runs ``find_missing_fields`` against each literal and
    raises ``RuntimeError`` on any divergence — that points the maintainer
    directly at the drifted agent rather than a confusing downstream
    evaluator failure.
    """
    from agents._validator import find_missing_fields

    literals: list[tuple[str, dict[str, Any]]] = [
        ("it_security_agent", _scenario_2_security_output()),
        ("legal_agent", _scenario_2_legal_output()),
        ("procurement_agent", _scenario_2_procurement_output()),
        ("checklist_assembler", _scenario_2_checklist_output()),
    ]
    drift: list[str] = []
    for agent, output in literals:
        missing = find_missing_fields(agent, output)
        if missing:
            drift.append(f"{agent}: missing={missing!r}")
    if drift:
        raise RuntimeError(
            "scenario_2 literal outputs in tests/support/bundle_builder.py "
            "drifted from current agent contracts — update the _scenario_2_* "
            "functions to match:\n  " + "\n  ".join(drift)
        )


def build_bundle_for(scenario: str, agent: str) -> dict[str, Any]:
    """Return the structured_fields bundle for a single (scenario, agent) pair."""
    bundles = build_bundles(scenario)
    if agent not in bundles:
        raise KeyError(f"no bundle for agent {agent!r} in {scenario!r}; known: {sorted(k for k in bundles if not k.startswith('_'))}")
    return bundles[agent]


def pipeline_run_id_for(scenario: str) -> str:
    bundles = build_bundles(scenario)
    return bundles.get("_pipeline_run_id", f"{scenario}_run")  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Mutation helpers for edge-case fixtures
# ---------------------------------------------------------------------------


def drop_key(bundle: dict[str, Any], path: str) -> dict[str, Any]:
    """Return a deep-copy of ``bundle`` with the dotted-path key removed.

    If any segment is absent the function is a no-op — the test is expected
    to verify the mutation succeeded via its own assertions.
    """
    out = deepcopy(bundle)
    segments = path.split(".")
    cursor: Any = out
    for seg in segments[:-1]:
        if isinstance(cursor, dict) and seg in cursor:
            cursor = cursor[seg]
        else:
            return out
    if isinstance(cursor, dict):
        cursor.pop(segments[-1], None)
    return out


def set_value(bundle: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Return a deep-copy of ``bundle`` with ``path`` set to ``value`` (creates parents)."""
    out = deepcopy(bundle)
    segments = path.split(".")
    cursor: Any = out
    for seg in segments[:-1]:
        if not isinstance(cursor, dict):
            return out
        cursor = cursor.setdefault(seg, {})
    if isinstance(cursor, dict):
        cursor[segments[-1]] = value
    return out
