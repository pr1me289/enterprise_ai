"""LLM-backed agent runner with a deterministic mock adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.agents.base import LLMAdapter


SPEC_PATHS = {
    "it_security_agent": Path("agent_spec_docs/IT_Security_Agent_Spec.md"),
    "legal_agent": Path("agent_spec_docs/Legal_Agent_Spec.md"),
    "procurement_agent": Path("agent_spec_docs/Procurement_Agent_Spec.md"),
    "checklist_assembler": Path("agent_spec_docs/Checklist_Assembler_Spec.md"),
    "checkoff_agent": Path("agent_spec_docs/Checkoff_Agent_Spec.md"),
}


class LLMAgentRunner:
    """Build prompts and invoke an adapter that returns structured JSON."""

    def __init__(self, *, repo_root: str | Path, adapter: LLMAdapter) -> None:
        self.repo_root = Path(repo_root)
        self.adapter = adapter

    def run(self, *, agent_name: str, bundle: Any, step_metadata: dict[str, Any]) -> dict[str, Any]:
        # Accept either a ContextBundle (typed) or a plain dict.  Agents always
        # receive the flat structured_fields dict so downstream logic is unchanged.
        bundle_dict: dict[str, Any] = (
            bundle.structured_fields if hasattr(bundle, "structured_fields") else bundle
        )
        spec_text = self._load_spec(agent_name)
        prompt = self._build_prompt(agent_name=agent_name, spec_text=spec_text, bundle=bundle_dict, step_metadata=step_metadata)
        return self.adapter.generate_structured_json(
            agent_name=agent_name,
            spec_text=spec_text,
            prompt=prompt,
            bundle=bundle_dict,
            step_metadata=step_metadata,
        )

    def _load_spec(self, agent_name: str) -> str:
        relative = SPEC_PATHS[agent_name]
        return (self.repo_root / relative).read_text(encoding="utf-8")

    def _build_prompt(
        self,
        *,
        agent_name: str,
        spec_text: str,
        bundle: dict[str, Any],
        step_metadata: dict[str, Any],
    ) -> str:
        return (
            f"You are {agent_name}.\n"
            "Use only the provided evidence bundle.\n"
            "Obey the attached agent spec as source of truth.\n"
            "Do not perform retrieval.\n"
            "Do not invent sources.\n"
            "Emit only structured JSON matching the required output contract.\n\n"
            f"Step metadata:\n{json.dumps(step_metadata, indent=2, sort_keys=True)}\n\n"
            f"Evidence bundle:\n{json.dumps(bundle, indent=2, sort_keys=True)}\n\n"
            f"Agent spec:\n{spec_text}"
        )


class MockLLMAdapter:
    """Deterministic adapter used for the first-pass orchestration demo."""

    def generate_structured_json(
        self,
        *,
        agent_name: str,
        spec_text: str,
        prompt: str,
        bundle: dict[str, Any],
        step_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        del spec_text, prompt, step_metadata
        if agent_name == "it_security_agent":
            return self._run_it_security(bundle)
        if agent_name == "legal_agent":
            return self._run_legal(bundle)
        if agent_name == "procurement_agent":
            return self._run_procurement(bundle)
        if agent_name == "checklist_assembler":
            return self._run_checklist(bundle)
        if agent_name == "checkoff_agent":
            return self._run_checkoff(bundle)
        raise KeyError(f"Unsupported mock agent: {agent_name}")

    def _run_it_security(self, bundle: dict[str, Any]) -> dict[str, Any]:
        meta = bundle["bundle_meta"]
        questionnaire = bundle["questionnaire"]
        if meta["missing_fields"] or meta["prohibited_sources"]:
            return {"status": "blocked", "errors": meta["missing_fields"] + meta["prohibited_sources"]}

        integration_raw = str(questionnaire["integration_details.erp_type"])
        description = str(questionnaire["integration_details.integration_description"])
        eu_flag = questionnaire["eu_personal_data_flag"]
        personal_data = questionnaire["data_classification_self_reported"]
        regulated_types = questionnaire["regulated_data_types"]

        if "UNCLASSIFIED" in integration_raw.upper():
            integration_type = "AMBIGUOUS"
            integration_tier = "UNCLASSIFIED_PENDING_REVIEW"
        elif "middleware" in description.lower():
            integration_type = "MIDDLEWARE"
            integration_tier = "TIER_2"
        elif "export" in description.lower() or "sftp" in description.lower():
            integration_type = "EXPORT_ONLY"
            integration_tier = "TIER_3"
        else:
            integration_type = "DIRECT_API"
            integration_tier = "TIER_1"

        eu_present = "YES" if eu_flag is True else "NO" if eu_flag is False else "UNKNOWN"
        is_regulated = bool(personal_data) or bool(eu_flag) or any("employee" in str(item).lower() for item in regulated_types)
        data_classification = "REGULATED" if is_regulated else "UNREGULATED"
        nda_status = _normalize_nda_status(questionnaire["existing_nda_status"])

        security_followup = (
            integration_tier == "UNCLASSIFIED_PENDING_REVIEW"
            or data_classification == "REGULATED"
            or integration_type == "AMBIGUOUS"
        )
        fast_track_eligible = data_classification == "UNREGULATED" and integration_type == "EXPORT_ONLY"
        if data_classification == "REGULATED":
            fast_track_rationale = "DISALLOWED_REGULATED_DATA"
        elif integration_type == "AMBIGUOUS":
            fast_track_rationale = "DISALLOWED_AMBIGUOUS_SCOPE"
        elif integration_tier in {"TIER_1", "TIER_2"}:
            fast_track_rationale = "DISALLOWED_INTEGRATION_RISK"
        else:
            fast_track_rationale = "ELIGIBLE_LOW_RISK"

        citations = _policy_citations(
            *bundle["policy_chunks"]["erp_tier_policy_chunks"],
            *bundle["policy_chunks"]["classification_policy_chunks"],
            *bundle["policy_chunks"]["fast_track_policy_chunks"],
        )
        return {
            "integration_type_normalized": integration_type,
            "integration_tier": integration_tier,
            "data_classification": data_classification,
            "eu_personal_data_present": eu_present,
            "fast_track_eligible": fast_track_eligible,
            "fast_track_rationale": fast_track_rationale,
            "security_followup_required": security_followup,
            "nda_status_from_questionnaire": nda_status,
            "required_security_actions": (
                [{"action_type": "SECURITY_REVIEW", "reason": "Ambiguous or regulated integration requires review", "owner": "IT Security"}]
                if security_followup
                else []
            ),
            "policy_citations": citations,
            "status": "escalated" if integration_type == "AMBIGUOUS" else "complete",
        }

    def _run_legal(self, bundle: dict[str, Any]) -> dict[str, Any]:
        meta = bundle["bundle_meta"]
        if meta["prohibited_sources"] or "upstream_data_classification" in meta["missing_fields"]:
            return {"status": "blocked", "errors": meta["missing_fields"] + meta["prohibited_sources"]}

        security_output = bundle["security_output"]
        questionnaire = bundle["questionnaire"]
        eu_confirmed = bool(questionnaire.get("eu_personal_data_flag")) and bool(questionnaire.get("data_subjects_eu"))
        dpa_rows = bundle["dpa_trigger_rows"]
        nda_clause_chunks = bundle["nda_clause_chunks"]
        nda_status = _normalize_nda_status(questionnaire.get("existing_nda_status"))
        dpa_status_raw = str(questionnaire.get("dpa_status_raw", "UNKNOWN"))

        if security_output["data_classification"] == "REGULATED" or eu_confirmed:
            dpa_required = True
            dpa_blocker = "EXECUTED" not in dpa_status_raw.upper()
        else:
            dpa_required = False
            dpa_blocker = False

        nda_blocker = nda_status != "EXECUTED"
        trigger_rule_cited = [
            {
                "source_id": row["source_id"],
                "version": row["version"],
                "row_id": row["row_id"],
                "trigger_condition": row["text"][:120],
                "citation_class": "PRIMARY",
            }
            for row in dpa_rows[:2]
        ]
        policy_citations = _policy_citations(*dpa_rows, *nda_clause_chunks)

        if not nda_clause_chunks:
            status = "escalated"
        elif dpa_blocker or nda_blocker or meta["missing_fields"]:
            status = "escalated"
        else:
            status = "complete"

        return {
            "dpa_required": dpa_required,
            "dpa_blocker": dpa_blocker,
            "nda_status": nda_status,
            "nda_blocker": nda_blocker,
            "trigger_rule_cited": trigger_rule_cited,
            "policy_citations": policy_citations,
            "status": status,
        }

    def _run_procurement(self, bundle: dict[str, Any]) -> dict[str, Any]:
        meta = bundle["bundle_meta"]
        if meta["missing_fields"] or meta["prohibited_sources"]:
            return {"status": "blocked", "errors": meta["missing_fields"] + meta["prohibited_sources"]}

        security_output = bundle["it_security_output"]
        legal_output = bundle["legal_output"]
        vendor = bundle["questionnaire"]
        matrix_rows = bundle["approval_path_matrix_rows"]

        if not matrix_rows:
            return {
                "fast_track_eligible": security_output["fast_track_eligible"],
                "required_approvals": [],
                "estimated_timeline": "",
                "policy_citations": [],
                "status": "escalated",
            }

        approval_path = "FAST_TRACK" if security_output["fast_track_eligible"] else "STANDARD"
        if approval_path == "FAST_TRACK":
            required_approvals = [
                {
                    "approver": "Procurement Manager",
                    "domain": "procurement",
                    "status": "PENDING",
                    "blocker": False,
                    "estimated_completion": "2 business days",
                }
            ]
            estimated_timeline = "2 business days"
        else:
            required_approvals = [
                {
                    "approver": "IT Security",
                    "domain": "security",
                    "status": "PENDING",
                    "blocker": legal_output["nda_blocker"] or legal_output["dpa_blocker"],
                    "estimated_completion": "3 business days",
                },
                {
                    "approver": "Legal (General Counsel)",
                    "domain": "legal",
                    "status": "PENDING",
                    "blocker": legal_output["dpa_blocker"],
                    "estimated_completion": "5 business days",
                },
                {
                    "approver": "Procurement Director",
                    "domain": "procurement",
                    "status": "PENDING",
                    "blocker": False,
                    "estimated_completion": "5 business days",
                },
            ]
            estimated_timeline = "5 business days"

        status = "complete"
        if legal_output["status"] != "complete":
            status = "escalated"
        policy_citations = [
            {
                "source_id": row["source_id"],
                "version": row["version"],
                "chunk_id": row["chunk_id"],
                "row_id": row["row_id"],
                "approval_path_condition": f"{vendor['vendor_class']} / {vendor['deal_size']}",
                "citation_class": "PRIMARY",
            }
            for row in matrix_rows[:2]
        ]
        return {
            "approval_path": approval_path,
            "fast_track_eligible": security_output["fast_track_eligible"],
            "required_approvals": required_approvals,
            "estimated_timeline": estimated_timeline,
            "policy_citations": policy_citations,
            "status": status,
        }

    def _run_checklist(self, bundle: dict[str, Any]) -> dict[str, Any]:
        meta = bundle["bundle_meta"]
        if meta["missing_fields"] or meta["prohibited_sources"]:
            return {
                "pipeline_run_id": bundle["pipeline_run_id"],
                "vendor_name": bundle["vendor_name"],
                "overall_status": "BLOCKED",
            }

        security = bundle["it_security_agent"]
        legal = bundle["legal_agent"]
        procurement = bundle["procurement_agent"]
        audit_entries = bundle["audit_log_entries"]

        upstream_statuses = (security["status"], legal["status"], procurement["status"])
        if any(status == "blocked" for status in upstream_statuses):
            overall_status = "BLOCKED"
        elif any(status == "escalated" for status in upstream_statuses):
            overall_status = "ESCALATED"
        else:
            overall_status = "COMPLETE"

        blockers = []
        if legal["dpa_blocker"]:
            blockers.append(
                {
                    "blocker_type": "DPA_REQUIRED",
                    "description": "A DPA must be executed before data exchange proceeds.",
                    "resolution_owner": "Legal (General Counsel)",
                    "citation": "legal_agent:dpa_blocker",
                }
            )
        if legal["nda_blocker"]:
            blockers.append(
                {
                    "blocker_type": "NDA_UNCONFIRMED",
                    "description": "NDA execution remains unconfirmed.",
                    "resolution_owner": "Procurement / Legal",
                    "citation": "legal_agent:nda_blocker",
                }
            )
        if security["status"] == "escalated":
            blockers.append(
                {
                    "blocker_type": "ESCALATION_PENDING",
                    "description": "Security classification requires human review.",
                    "resolution_owner": "IT Security",
                    "citation": "it_security_agent:status",
                }
            )

        citations = _assemble_checklist_citations(
            security["policy_citations"] + legal["policy_citations"] + procurement["policy_citations"],
            audit_entries,
        )
        return {
            "pipeline_run_id": bundle["pipeline_run_id"],
            "vendor_name": bundle["vendor_name"],
            "overall_status": overall_status,
            "data_classification": security["data_classification"],
            "dpa_required": legal["dpa_required"],
            "fast_track_eligible": security["fast_track_eligible"],
            "required_security_actions": security["required_security_actions"],
            "approval_path": procurement.get("approval_path"),
            "required_approvals": procurement.get("required_approvals", []),
            "blockers": blockers,
            "citations": citations,
        }

    def _run_checkoff(self, bundle: dict[str, Any]) -> dict[str, Any]:
        meta = bundle["bundle_meta"]
        if meta["missing_fields"] or meta["prohibited_sources"]:
            return {"status": "blocked"}

        checklist = bundle["finalized_checklist"]
        stakeholder_payload = bundle["stakeholder_map"]
        stakeholder_map = stakeholder_payload.get("stakeholder_map", {})

        roles = {
            approval["approver"] for approval in checklist.get("required_approvals", [])
        }
        roles.update(blocker["resolution_owner"] for blocker in checklist.get("blockers", []))
        if not roles:
            roles.add("Procurement")

        guidance_documents = []
        for role in sorted(roles):
            role_domain = stakeholder_map.get(role, {}).get("domain", "general")
            blockers_owned = [item for item in checklist.get("blockers", []) if item["resolution_owner"] == role]
            security_actions = [
                item for item in checklist.get("required_security_actions", [])
                if item["owner"] == role
            ]
            next_steps = [
                f"Review approval requirement for {approval['domain']}"
                for approval in checklist.get("required_approvals", [])
                if approval["approver"] == role
            ]
            next_steps.extend(
                f"Resolve blocker: {blocker['description']}" for blocker in blockers_owned
            )
            if not next_steps:
                next_steps = ["No action required at this stage."]
            guidance_documents.append(
                {
                    "stakeholder_role": role,
                    "domain": role_domain,
                    "instructions": (
                        f"Pipeline status is {checklist['overall_status']}. "
                        f"Review the approvals, blockers, and citations scoped to {role}."
                    ),
                    "blockers_owned": blockers_owned,
                    "required_security_actions": security_actions,
                    "next_steps": next_steps,
                    "citations": checklist.get("citations", []),
                }
            )

        return {"guidance_documents": guidance_documents, "status": "complete"}


def _normalize_nda_status(raw_value: Any) -> str:
    text = str(raw_value or "").upper()
    if "EXECUTED" in text:
        return "EXECUTED"
    if "PENDING" in text or "PROVISIONAL" in text or "DRAFT" in text:
        return "PENDING"
    if "NOT_STARTED" in text or "NOT STARTED" in text:
        return "NOT_STARTED"
    return "UNKNOWN"


def _policy_citations(*items: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    citations: list[dict[str, Any]] = []
    for item in items:
        key = (item["source_id"], item["chunk_id"])
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "source_id": item["source_id"],
                "version": item["version"],
                "chunk_id": item["chunk_id"],
                "section_id": item.get("section_id") or item.get("row_id") or item.get("thread_id"),
                "citation_class": "SUPPLEMENTARY" if item["source_id"] == "SLK-001" else "PRIMARY",
            }
        )
    return citations


def _assemble_checklist_citations(policy_citations: list[dict[str, Any]], audit_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timestamps_by_chunk: dict[str, str] = {}
    for entry in audit_entries:
        if entry["event_type"] != "RETRIEVAL":
            continue
        for chunk in entry.get("chunks_retrieved", []):
            chunk_id = chunk.get("chunk_id")
            if chunk_id and chunk_id not in timestamps_by_chunk:
                timestamps_by_chunk[chunk_id] = entry["timestamp"]

    citations: list[dict[str, Any]] = []
    for citation in policy_citations:
        citations.append(
            {
                "source_name": citation["source_id"],
                "version": citation["version"],
                "section": citation.get("section_id") or citation.get("chunk_id"),
                "retrieval_timestamp": timestamps_by_chunk.get(citation["chunk_id"], ""),
                "agent_id": _agent_id_for_source(citation["source_id"]),
            }
        )
    return citations


def _agent_id_for_source(source_id: str) -> str:
    if source_id == "ISP-001":
        return "it_security_agent"
    if source_id == "DPA-TM-001":
        return "legal_agent"
    if source_id in {"PAM-001", "SLK-001"}:
        return "procurement_agent"
    return "supervisor"
