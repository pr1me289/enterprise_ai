"""Per-step bundle assembly helpers."""

from __future__ import annotations

from typing import Any

from orchestration.models.context_bundle import ContextBundle, ExcludedChunk
from orchestration.models.contracts import RetrievalResult
from orchestration.models.enums import StepId
from orchestration.models.retrieved_chunk import RetrievedChunk

# Slack (SLK-001) is authority tier 3 and is never primary evidence.
_SLACK_SOURCE_ID = "SLK-001"
_SLACK_THREAD4_VENDOR_SCOPE = "optichain"  # Thread 4 is an OptiChain-unrelated vendor


def _resolve_admissibility(validation: dict[str, Any]) -> str:
    """Map a validation result dict to the canonical admissibility_status string.

    Rules:
    - ``ADMISSIBLE`` — admissible flag is True.
    - ``ESCALATION_REQUIRED`` — prohibited sources are present (authority governance violation).
    - ``PARTIAL`` — missing required fields but no prohibited sources.
    """
    if validation.get("admissible"):
        return "ADMISSIBLE"
    if validation.get("prohibited_sources"):
        return "ESCALATION_REQUIRED"
    return "PARTIAL"


def _collect_chunks_from_result(result: RetrievalResult) -> list[RetrievedChunk]:
    """Return typed RetrievedChunk objects from a result, if any were produced."""
    return list(result.retrieved_chunks)


def _apply_slack_supplementary_rule(chunk: RetrievedChunk) -> RetrievedChunk:
    """Ensure Slack chunks are never marked as primary-citable evidence."""
    if chunk.source_id == _SLACK_SOURCE_ID and chunk.is_primary_citable:
        # Return a new chunk with is_primary_citable forced to False.
        return RetrievedChunk(
            source_id=chunk.source_id,
            source_name=chunk.source_name,
            source_type=chunk.source_type,
            chunk_id=chunk.chunk_id,
            authority_tier=chunk.authority_tier,
            retrieval_lane=chunk.retrieval_lane,
            is_primary_citable=False,
            text=chunk.text,
            citation_label=chunk.citation_label,
            extra_metadata=dict(chunk.extra_metadata),
        )
    return chunk


def _is_thread4_non_optichain(chunk: RetrievedChunk) -> bool:
    """Return True if this Slack chunk should be excluded from OptiChain determination bundles.

    Two exclusion criteria:
    1. The chunk carries an explicit Thread 4 identifier (``thread_id`` in ``T4``, ``4``,
       ``thread_4``).  Thread 4 covers Greenbrook Catering — an unrelated vendor — and must
       never appear in OptiChain determination bundles.
    2. The chunk carries a non-empty ``domain_scope`` that does not include ``"optichain"``,
       meaning it is explicitly scoped to a different vendor and must also be excluded.

    Non-Slack chunks are never subject to this rule.
    """
    if chunk.source_id != _SLACK_SOURCE_ID:
        return False
    thread_id = str(chunk.extra_metadata.get("thread_id", ""))
    # Match "T4", "4", "thread_4" — all are representations of thread 4.
    if thread_id in ("T4", "4", "thread_4"):
        return True
    domain_scope = chunk.extra_metadata.get("domain_scope", "")
    if domain_scope and _SLACK_THREAD4_VENDOR_SCOPE not in domain_scope.lower():
        return True
    return False


def _build_provenance(source_ids: list[str], retrieval_results: dict[str, RetrievalResult]) -> list[dict[str, Any]]:
    """Produce source-level provenance records."""
    seen: set[str] = set()
    provenance: list[dict[str, Any]] = []
    for key, result in retrieval_results.items():
        sid = result.request.source_id
        if sid not in seen:
            seen.add(sid)
            provenance.append(
                {
                    "source_id": sid,
                    "output_name": result.request.output_name,
                    "lane": result.request.lane.value,
                    "chunk_count": len(result.retrieved_chunks),
                }
            )
    return provenance


class BundleAssembler:
    """Build narrowly scoped bundles for each step from routed evidence."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assemble_chunks(
        self,
        step_id: StepId,
        retrieval_results: dict[str, RetrievalResult],
        *,
        optichain_context: bool = True,
    ) -> tuple[list[RetrievedChunk], list[ExcludedChunk]]:
        """Collect, filter, and classify evidence chunks for a step bundle."""
        admitted: list[RetrievedChunk] = []
        excluded: list[ExcludedChunk] = []

        for _key, result in retrieval_results.items():
            # Handle permission-denied excluded items from the router.
            for item in result.excluded_items:
                if "reason" in item:
                    # Create a stub chunk to carry the exclusion record.
                    stub = RetrievedChunk(
                        source_id=item.get("source_id", "UNKNOWN"),
                        source_name=item.get("source_id", "UNKNOWN"),
                        source_type="UNKNOWN",
                        chunk_id="permission_denied",
                        authority_tier=99,
                        retrieval_lane=result.request.lane.value,
                        is_primary_citable=False,
                        text="",
                        citation_label="",
                    )
                    excluded.append(ExcludedChunk(chunk=stub, exclusion_reason=item["reason"]))

            for chunk in _collect_chunks_from_result(result):
                # Rule: Thread 4 Slack chunks excluded for OptiChain determinations.
                if optichain_context and _is_thread4_non_optichain(chunk):
                    excluded.append(
                        ExcludedChunk(
                            chunk=chunk,
                            exclusion_reason="thread_4_excluded_non_optichain_vendor",
                        )
                    )
                    continue

                # Rule: Slack chunks must be supplementary only.
                chunk = _apply_slack_supplementary_rule(chunk)
                admitted.append(chunk)

        return admitted, excluded

    def _collect_structured_fields(
        self,
        result_keys: list[str],
        retrieval_results: dict[str, RetrievalResult],
    ) -> dict[str, Any]:
        """Merge structured payload fields from direct-structured results."""
        merged: dict[str, Any] = {}
        for key in result_keys:
            if key in retrieval_results:
                payload = retrieval_results[key].payload
                if isinstance(payload, dict):
                    merged.update(payload)
        return merged

    # ------------------------------------------------------------------
    # Per-step assembly producing ContextBundle
    # ------------------------------------------------------------------

    def assemble_step02(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> ContextBundle:
        step_id = StepId.STEP_02
        questionnaire: dict[str, Any] = {}
        for key in ("integration_inputs", "classification_inputs", "eu_inputs", "nda_inputs"):
            questionnaire.update(retrievals[key].payload)

        admitted, excluded = self._assemble_chunks(step_id, retrievals, optichain_context=True)
        provenance = _build_provenance(["VQ-OC-001", "ISP-001"], retrievals)
        admissibility = _resolve_admissibility(validation)

        bundle = ContextBundle(
            step_id=step_id,
            admitted_evidence=admitted,
            excluded_evidence=excluded,
            structured_fields={
                "questionnaire": questionnaire,
                "policy_chunks": {
                    "erp_tier_policy_chunks": retrievals["erp_tier_policy_chunks"].payload,
                    "classification_policy_chunks": retrievals["classification_policy_chunks"].payload,
                    "fast_track_policy_chunks": retrievals["fast_track_policy_chunks"].payload,
                    "nda_policy_chunks": retrievals["nda_policy_chunks"].payload,
                },
                "bundle_meta": validation,
                "source_ids": ["VQ-OC-001", "ISP-001"],
            },
            source_provenance=provenance,
            admissibility_status=admissibility,
        )
        return bundle

    def assemble_step03(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> ContextBundle:
        step_id = StepId.STEP_03
        admitted, excluded = self._assemble_chunks(step_id, retrievals, optichain_context=True)
        provenance = _build_provenance(["STEP-02", "VQ-OC-001", "DPA-TM-001", "ISP-001"], retrievals)
        admissibility = _resolve_admissibility(validation)

        upstream_security_payload = retrievals["upstream_security"].payload
        questionnaire = {
            **retrievals["eu_inputs"].payload,
            **retrievals["nda_inputs"].payload,
            **retrievals["dpa_status"].payload,
        }

        bundle = ContextBundle(
            step_id=step_id,
            admitted_evidence=admitted,
            excluded_evidence=excluded,
            structured_fields={
                "source_ids": ["STEP-02", "VQ-OC-001", "DPA-TM-001", "ISP-001"],
                "security_output": {
                    "data_classification": upstream_security_payload.get("upstream_data_classification"),
                    "status": upstream_security_payload.get("status"),
                    "policy_citations": upstream_security_payload.get("policy_citations", []),
                },
                "questionnaire": questionnaire,
                "dpa_trigger_rows": retrievals["dpa_trigger_rows"].payload,
                "nda_clause_chunks": retrievals["nda_clause_chunks"].payload,
                "bundle_meta": validation,
            },
            source_provenance=provenance,
            admissibility_status=admissibility,
        )
        return bundle

    def assemble_step04(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> ContextBundle:
        step_id = StepId.STEP_04
        admitted, excluded = self._assemble_chunks(step_id, retrievals, optichain_context=True)
        provenance = _build_provenance(["STEP-02", "STEP-03", "VQ-OC-001", "PAM-001", "SLK-001"], retrievals)
        admissibility = _resolve_admissibility(validation)

        bundle = ContextBundle(
            step_id=step_id,
            admitted_evidence=admitted,
            excluded_evidence=excluded,
            structured_fields={
                "source_ids": ["STEP-02", "STEP-03", "VQ-OC-001", "PAM-001", "SLK-001"],
                "it_security_output": retrievals["it_security_output"].payload,
                "legal_output": retrievals["legal_output"].payload,
                "questionnaire": retrievals["vendor_relationship"].payload,
                "approval_path_matrix_rows": retrievals["approval_matrix_rows"].payload,
                "fast_track_routing_rows": retrievals["fast_track_rows"].payload,
                "slack_procurement_chunks": retrievals["slack_procurement"].payload,
                "bundle_meta": validation,
            },
            source_provenance=provenance,
            admissibility_status=admissibility,
        )
        return bundle

    def assemble_step05(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> ContextBundle:
        step_id = StepId.STEP_05
        domain_outputs = retrievals["all_agent_outputs"].payload
        admitted, excluded = self._assemble_chunks(step_id, retrievals, optichain_context=True)
        provenance = _build_provenance(["STEP-02", "STEP-03", "STEP-04", "AUDIT_LOG", "VQ-OC-001"], retrievals)
        admissibility = _resolve_admissibility(validation)

        bundle = ContextBundle(
            step_id=step_id,
            admitted_evidence=admitted,
            excluded_evidence=excluded,
            structured_fields={
                "source_ids": ["STEP-02", "STEP-03", "STEP-04", "AUDIT_LOG", "VQ-OC-001"],
                "pipeline_run_id": retrievals["pipeline_state"].payload.get("pipeline_run_id"),
                "vendor_name": retrievals["questionnaire_header"].payload.get("vendor_name"),
                "it_security_agent": domain_outputs.get("it_security_agent"),
                "legal_agent": domain_outputs.get("legal_agent"),
                "procurement_agent": domain_outputs.get("procurement_agent"),
                "audit_log_entries": retrievals["audit_log"].payload.get("entries", []),
                "bundle_meta": validation,
            },
            source_provenance=provenance,
            admissibility_status=admissibility,
        )
        return bundle

    def assemble_step06(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> ContextBundle:
        step_id = StepId.STEP_06
        admitted, excluded = self._assemble_chunks(step_id, retrievals, optichain_context=True)
        provenance = _build_provenance(["STEP-05", "PIPELINE_CONFIG", "STEP-02", "STEP-03", "STEP-04"], retrievals)
        admissibility = _resolve_admissibility(validation)

        bundle = ContextBundle(
            step_id=step_id,
            admitted_evidence=admitted,
            excluded_evidence=excluded,
            structured_fields={
                "source_ids": ["STEP-05", "PIPELINE_CONFIG", "STEP-02", "STEP-03", "STEP-04"],
                "finalized_checklist": retrievals["finalized_checklist"].payload,
                "stakeholder_map": retrievals["stakeholder_map"].payload,
                "domain_outputs": retrievals["domain_outputs"].payload,
                "bundle_meta": validation,
            },
            source_provenance=provenance,
            admissibility_status=admissibility,
        )
        return bundle
