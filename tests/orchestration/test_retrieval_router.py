"""Tests for retrieval router typed output and bundle assembler ContextBundle production."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from orchestration.models.context_bundle import ContextBundle
from orchestration.models.contracts import RetrievalRequest, RetrievalResult
from orchestration.models.enums import RetrievalLane, StepId
from orchestration.models.retrieved_chunk import RetrievedChunk
from orchestration.retrieval.bundle_assembler import BundleAssembler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_chunk_dict(
    source_id: str = "ISP-001",
    chunk_id: str = "ISP-001__section_12",
    authority_tier: int = 1,
    is_primary_citable: bool = True,
    retrieval_lane: str = "indexed_hybrid",
    source_name: str = "IT Security Policy",
    source_type: str = "POLICY_DOCUMENT",
    text: str = "ERP integrations are classified by tier.",
    citation_label: str = "ISP-001 §12",
    thread_id: str | None = None,
    domain_scope: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a raw chunk dict as returned by MockHybridIndexedBackend.query()."""
    d: dict[str, Any] = {
        "source_id": source_id,
        "source_name": source_name,
        "source_type": source_type,
        "chunk_id": chunk_id,
        "authority_tier": authority_tier,
        "retrieval_lane": retrieval_lane,
        "is_primary_citable": is_primary_citable,
        "text": text,
        "citation_label": citation_label,
        "retrieval_score": 1.0,
        "rerank_score": 1.0,
    }
    if thread_id is not None:
        d["thread_id"] = thread_id
    if domain_scope is not None:
        d["domain_scope"] = domain_scope
    d.update(extra)
    return d


def _make_slack_chunk_dict(
    thread_id: str = "T1",
    is_primary_citable: bool = False,
    domain_scope: str | None = None,
) -> dict[str, Any]:
    return _make_chunk_dict(
        source_id="SLK-001",
        source_name="Slack / Meeting Thread Notes",
        source_type="SLACK_THREAD",
        chunk_id=f"SLK-001__thread_{thread_id}",
        authority_tier=3,
        is_primary_citable=is_primary_citable,
        citation_label=f"SLK-001 thread {thread_id}",
        text=f"Slack thread {thread_id} text.",
        thread_id=thread_id,
        domain_scope=domain_scope,
    )


def _make_retrieval_result(
    source_id: str = "ISP-001",
    output_name: str = "policy_chunks",
    lane: RetrievalLane = RetrievalLane.INDEXED_HYBRID,
    hits: list[dict[str, Any]] | None = None,
    payload: Any = None,
    excluded_items: list[dict[str, Any]] | None = None,
) -> RetrievalResult:
    """Build a RetrievalResult as produced by the router after our changes."""
    from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

    hits = hits or []
    typed_chunks = [_chunk_dict_to_retrieved_chunk(h) for h in hits]
    return RetrievalResult(
        request=RetrievalRequest(
            request_id="TEST-001",
            lane=lane,
            source_id=source_id,
            access_role="it_security",
            output_name=output_name,
        ),
        payload=payload if payload is not None else hits,
        admitted_items=hits,
        excluded_items=excluded_items or [],
        retrieved_chunks=typed_chunks,
    )


def _make_direct_result(
    source_id: str = "VQ-OC-001",
    output_name: str = "questionnaire_field",
    payload: dict[str, Any] | None = None,
) -> RetrievalResult:
    payload = payload or {}
    return RetrievalResult(
        request=RetrievalRequest(
            request_id="TEST-DS-001",
            lane=RetrievalLane.DIRECT_STRUCTURED,
            source_id=source_id,
            access_role="it_security",
            output_name=output_name,
            field_map={"field_key": ("field.path",)},
        ),
        payload=payload,
        admitted_items=[{"field_path": k, "value_present": True} for k in payload],
    )


# ---------------------------------------------------------------------------
# Tests: _chunk_dict_to_retrieved_chunk conversion
# ---------------------------------------------------------------------------


class TestChunkDictToRetrievedChunk:
    def test_basic_conversion_returns_retrieved_chunk(self) -> None:
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = _make_chunk_dict()
        chunk = _chunk_dict_to_retrieved_chunk(hit)

        assert isinstance(chunk, RetrievedChunk)
        assert chunk.source_id == "ISP-001"
        assert chunk.chunk_id == "ISP-001__section_12"
        assert chunk.authority_tier == 1
        assert chunk.is_primary_citable is True
        assert chunk.text == "ERP integrations are classified by tier."
        assert chunk.citation_label == "ISP-001 §12"
        assert chunk.retrieval_lane == "indexed_hybrid"

    def test_extra_fields_go_into_extra_metadata(self) -> None:
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = _make_chunk_dict(retrieval_score=0.95, rerank_score=0.8, version="4.2", section_id="12")
        chunk = _chunk_dict_to_retrieved_chunk(hit)

        assert chunk.extra_metadata["retrieval_score"] == 0.95
        assert chunk.extra_metadata["version"] == "4.2"
        assert chunk.extra_metadata["section_id"] == "12"

    def test_slack_chunk_conversion_preserves_thread_id(self) -> None:
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = _make_slack_chunk_dict(thread_id="T1")
        chunk = _chunk_dict_to_retrieved_chunk(hit)

        assert chunk.source_id == "SLK-001"
        assert chunk.authority_tier == 3
        assert chunk.is_primary_citable is False
        assert chunk.extra_metadata.get("thread_id") == "T1"


# ---------------------------------------------------------------------------
# Tests: Router returns RetrievedChunk objects for INDEXED_HYBRID
# ---------------------------------------------------------------------------


class TestRouterIndexedHybridTypedOutput:
    def _make_router(self, hits: list[dict[str, Any]], source_id: str = "ISP-001") -> Any:
        """Build a router with mocked backends returning the given hits."""
        from orchestration.audit.audit_logger import AuditLogger
        from orchestration.retrieval.router import RetrievalRouter

        mock_direct = MagicMock()
        mock_indexed = MagicMock()
        mock_indexed.query.return_value = hits
        mock_runtime = MagicMock()
        mock_runtime.read.return_value = ({}, [])
        audit = AuditLogger(pipeline_run_id="test-run")

        # Patch _check_index_access to always allow
        router = RetrievalRouter(
            direct_accessor=mock_direct,
            indexed_backend=mock_indexed,
            runtime_accessor=mock_runtime,
            audit_logger=audit,
        )
        router._check_index_access = lambda access_role, src_id: (False, "")  # type: ignore[method-assign]
        return router

    def test_indexed_hybrid_result_has_retrieved_chunks(self) -> None:
        hits = [_make_chunk_dict(), _make_chunk_dict(chunk_id="ISP-001__section_17", citation_label="ISP-001 §17")]
        router = self._make_router(hits)
        mock_state = MagicMock()
        request = RetrievalRequest(
            request_id="TEST-IDX-001",
            lane=RetrievalLane.INDEXED_HYBRID,
            source_id="ISP-001",
            access_role="it_security",
            output_name="policy_chunks",
            search_terms=("ERP tier",),
        )
        result = router.route(request, state=mock_state)

        assert len(result.retrieved_chunks) == 2
        assert all(isinstance(c, RetrievedChunk) for c in result.retrieved_chunks)

    def test_indexed_hybrid_chunks_have_correct_attributes(self) -> None:
        hits = [_make_chunk_dict(chunk_id="ISP-001__section_12", citation_label="ISP-001 §12", authority_tier=1)]
        router = self._make_router(hits)
        mock_state = MagicMock()
        request = RetrievalRequest(
            request_id="TEST-IDX-002",
            lane=RetrievalLane.INDEXED_HYBRID,
            source_id="ISP-001",
            access_role="it_security",
            output_name="erp_tier",
            search_terms=("ERP tier",),
        )
        result = router.route(request, state=mock_state)

        chunk = result.retrieved_chunks[0]
        assert chunk.source_id == "ISP-001"
        assert chunk.chunk_id == "ISP-001__section_12"
        assert chunk.citation_label == "ISP-001 §12"
        assert chunk.authority_tier == 1

    def test_indexed_hybrid_empty_result_has_empty_retrieved_chunks(self) -> None:
        router = self._make_router([])
        mock_state = MagicMock()
        request = RetrievalRequest(
            request_id="TEST-IDX-003",
            lane=RetrievalLane.INDEXED_HYBRID,
            source_id="ISP-001",
            access_role="it_security",
            output_name="policy_chunks",
            search_terms=("no match",),
        )
        result = router.route(request, state=mock_state)

        assert result.retrieved_chunks == []
        assert result.payload == []

    def test_direct_structured_has_no_retrieved_chunks(self) -> None:
        from orchestration.audit.audit_logger import AuditLogger
        from orchestration.retrieval.router import RetrievalRouter

        mock_direct = MagicMock()
        mock_direct.read_fields.return_value = ({"erp_type": "EXPORT_ONLY"}, [])
        mock_indexed = MagicMock()
        mock_runtime = MagicMock()
        audit = AuditLogger(pipeline_run_id="test-run-ds")
        router = RetrievalRouter(
            direct_accessor=mock_direct,
            indexed_backend=mock_indexed,
            runtime_accessor=mock_runtime,
            audit_logger=audit,
        )
        mock_state = MagicMock()
        request = RetrievalRequest(
            request_id="TEST-DS-001",
            lane=RetrievalLane.DIRECT_STRUCTURED,
            source_id="VQ-OC-001",
            access_role="it_security",
            output_name="integration_inputs",
            field_map={"erp_type": ("product_and_integration.erp_integration.erp_type",)},
        )
        result = router.route(request, state=mock_state)

        assert result.retrieved_chunks == []
        assert result.payload == {"erp_type": "EXPORT_ONLY"}


# ---------------------------------------------------------------------------
# Tests: Source permission enforcement
# ---------------------------------------------------------------------------


class TestSourcePermissionEnforcement:
    def test_permission_denied_returns_empty_result_with_excluded_item(self) -> None:
        from orchestration.audit.audit_logger import AuditLogger
        from orchestration.retrieval.router import RetrievalRouter

        mock_direct = MagicMock()
        mock_indexed = MagicMock()
        mock_indexed.query.return_value = []
        mock_runtime = MagicMock()
        audit = AuditLogger(pipeline_run_id="test-perm")
        router = RetrievalRouter(
            direct_accessor=mock_direct,
            indexed_backend=mock_indexed,
            runtime_accessor=mock_runtime,
            audit_logger=audit,
        )
        # Simulate a role that is not in allowed_agents
        router._check_index_access = lambda role, src: (True, f"'{role}' not permitted for {src}")  # type: ignore[method-assign]

        mock_state = MagicMock()
        request = RetrievalRequest(
            request_id="TEST-PERM-001",
            lane=RetrievalLane.INDEXED_HYBRID,
            source_id="SLK-001",
            access_role="it_security",  # it_security not allowed for SLK-001
            output_name="slack_chunks",
            search_terms=("approval",),
        )
        result = router.route(request, state=mock_state)

        assert result.payload == []
        assert result.retrieved_chunks == []
        assert len(result.excluded_items) == 1
        assert "not permitted" in result.excluded_items[0]["reason"]

    def test_check_index_access_unknown_source_returns_denial(self) -> None:
        from orchestration.audit.audit_logger import AuditLogger
        from orchestration.retrieval.router import RetrievalRouter

        audit = AuditLogger(pipeline_run_id="test-unknown")
        router = RetrievalRouter(
            direct_accessor=MagicMock(),
            indexed_backend=MagicMock(),
            runtime_accessor=MagicMock(),
            audit_logger=audit,
        )
        denied, reason = router._check_index_access("supervisor", "NONEXISTENT-001")
        assert denied is True
        assert "NONEXISTENT-001" in reason


# ---------------------------------------------------------------------------
# Tests: BundleAssembler produces ContextBundle
# ---------------------------------------------------------------------------


def _minimal_step02_retrievals() -> dict[str, RetrievalResult]:
    """Minimal retrievals dict for step 02 assembly."""
    isp_hit = _make_chunk_dict(chunk_id="ISP-001__section_12", citation_label="ISP-001 §12")
    return {
        "integration_inputs": _make_direct_result(payload={"integration_details.erp_type": "EXPORT_ONLY"}),
        "classification_inputs": _make_direct_result(payload={"data_classification_self_reported": False}),
        "eu_inputs": _make_direct_result(payload={"eu_personal_data_flag": False}),
        "nda_inputs": _make_direct_result(payload={"existing_nda_status": "EXECUTED"}),
        "erp_tier_policy_chunks": _make_retrieval_result(source_id="ISP-001", output_name="erp_tier_policy_chunks", hits=[isp_hit]),
        "classification_policy_chunks": _make_retrieval_result(source_id="ISP-001", output_name="classification_policy_chunks", hits=[isp_hit]),
        "fast_track_policy_chunks": _make_retrieval_result(source_id="ISP-001", output_name="fast_track_policy_chunks", hits=[isp_hit]),
        "nda_policy_chunks": _make_retrieval_result(source_id="ISP-001", output_name="nda_policy_chunks", hits=[isp_hit]),
    }


def _admissible_validation() -> dict[str, Any]:
    return {"admissible": True, "missing_fields": [], "prohibited_sources": []}


class TestBundleAssemblerProducesContextBundle:
    def test_assemble_step02_returns_context_bundle(self) -> None:
        assembler = BundleAssembler()
        retrievals = _minimal_step02_retrievals()
        bundle = assembler.assemble_step02(retrievals, _admissible_validation())

        assert isinstance(bundle, ContextBundle)
        assert bundle.step_id == StepId.STEP_02
        assert bundle.admissibility_status == "ADMISSIBLE"

    def test_assemble_step02_admitted_evidence_typed_chunks(self) -> None:
        assembler = BundleAssembler()
        retrievals = _minimal_step02_retrievals()
        bundle = assembler.assemble_step02(retrievals, _admissible_validation())

        assert all(isinstance(c, RetrievedChunk) for c in bundle.admitted_evidence)

    def test_assemble_step02_structured_fields_contains_questionnaire(self) -> None:
        assembler = BundleAssembler()
        retrievals = _minimal_step02_retrievals()
        bundle = assembler.assemble_step02(retrievals, _admissible_validation())

        assert "questionnaire" in bundle.structured_fields
        assert "bundle_meta" in bundle.structured_fields

    def test_assemble_step02_partial_when_not_admissible(self) -> None:
        assembler = BundleAssembler()
        retrievals = _minimal_step02_retrievals()
        validation = {"admissible": False, "missing_fields": ["eu_personal_data_flag"], "prohibited_sources": []}
        bundle = assembler.assemble_step02(retrievals, validation)

        assert bundle.admissibility_status == "PARTIAL"

    def test_assemble_step02_to_dict_round_trip(self) -> None:
        assembler = BundleAssembler()
        retrievals = _minimal_step02_retrievals()
        bundle = assembler.assemble_step02(retrievals, _admissible_validation())
        d = bundle.to_dict()

        assert d["step_id"] == "STEP-02"
        assert "admitted_evidence" in d
        assert "excluded_evidence" in d
        assert "structured_fields" in d
        assert d["admissibility_status"] == "ADMISSIBLE"

    def test_assemble_step02_source_provenance_populated(self) -> None:
        assembler = BundleAssembler()
        retrievals = _minimal_step02_retrievals()
        bundle = assembler.assemble_step02(retrievals, _admissible_validation())

        assert len(bundle.source_provenance) > 0
        source_ids = [p["source_id"] for p in bundle.source_provenance]
        assert "ISP-001" in source_ids


# ---------------------------------------------------------------------------
# Tests: Slack supplementary-only rule enforcement
# ---------------------------------------------------------------------------


class TestSlackSupplementaryRule:
    def test_slack_chunk_is_primary_citable_forced_false(self) -> None:
        """A Slack chunk with is_primary_citable=True must be demoted to False."""
        from orchestration.retrieval.bundle_assembler import _apply_slack_supplementary_rule

        slack_hit = _make_slack_chunk_dict(thread_id="T1", is_primary_citable=True)

        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        chunk = _chunk_dict_to_retrieved_chunk(slack_hit)
        assert chunk.is_primary_citable is True  # Raw value

        corrected = _apply_slack_supplementary_rule(chunk)
        assert corrected.is_primary_citable is False

    def test_slack_chunk_already_false_is_unchanged(self) -> None:
        from orchestration.retrieval.bundle_assembler import _apply_slack_supplementary_rule
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        slack_hit = _make_slack_chunk_dict(thread_id="T2", is_primary_citable=False)
        chunk = _chunk_dict_to_retrieved_chunk(slack_hit)
        corrected = _apply_slack_supplementary_rule(chunk)
        # Should return the same object unchanged
        assert corrected is chunk

    def test_non_slack_chunk_is_unaffected(self) -> None:
        from orchestration.retrieval.bundle_assembler import _apply_slack_supplementary_rule
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        isp_hit = _make_chunk_dict(is_primary_citable=True)
        chunk = _chunk_dict_to_retrieved_chunk(isp_hit)
        corrected = _apply_slack_supplementary_rule(chunk)
        assert corrected.is_primary_citable is True

    def test_bundle_assembler_enforces_slack_supplementary_in_step04(self) -> None:
        """In step04 bundles that include Slack, no Slack chunk should be primary_citable."""
        slack_hit_primary = _make_slack_chunk_dict(thread_id="T1", is_primary_citable=True)
        pam_hit = _make_chunk_dict(
            source_id="PAM-001",
            chunk_id="PAM-001__row_A",
            source_name="Procurement Approval Matrix",
            source_type="STRUCTURED_TABLE",
            citation_label="PAM-001 row A",
        )

        retrievals: dict[str, RetrievalResult] = {
            "it_security_output": _make_direct_result(payload={"data_classification": "UNREGULATED", "fast_track_eligible": True}),
            "legal_output": _make_direct_result(payload={"dpa_required": False, "nda_status": "EXECUTED"}),
            "vendor_relationship": _make_direct_result(payload={"vendor_class": "CLASS_A", "deal_size": 50000}),
            "approval_matrix_rows": _make_retrieval_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
            "fast_track_rows": _make_retrieval_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
            "slack_procurement": _make_retrieval_result(
                source_id="SLK-001",
                output_name="slack_procurement",
                hits=[slack_hit_primary],
            ),
        }

        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(retrievals, _admissible_validation())

        slack_chunks = [c for c in bundle.admitted_evidence if c.source_id == "SLK-001"]
        for sc in slack_chunks:
            assert sc.is_primary_citable is False, f"Slack chunk {sc.chunk_id} must not be primary-citable"


# ---------------------------------------------------------------------------
# Tests: Thread 4 exclusion for OptiChain determinations
# ---------------------------------------------------------------------------


class TestThread4Exclusion:
    def test_thread4_excluded_from_optichain_bundle(self) -> None:
        from orchestration.retrieval.bundle_assembler import _is_thread4_non_optichain
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        t4_hit = _make_slack_chunk_dict(thread_id="T4")
        chunk = _chunk_dict_to_retrieved_chunk(t4_hit)
        assert _is_thread4_non_optichain(chunk) is True

    def test_thread1_not_excluded(self) -> None:
        from orchestration.retrieval.bundle_assembler import _is_thread4_non_optichain
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        t1_hit = _make_slack_chunk_dict(thread_id="T1")
        chunk = _chunk_dict_to_retrieved_chunk(t1_hit)
        assert _is_thread4_non_optichain(chunk) is False

    def test_isp_chunk_never_treated_as_thread4(self) -> None:
        from orchestration.retrieval.bundle_assembler import _is_thread4_non_optichain
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        isp_hit = _make_chunk_dict()
        chunk = _chunk_dict_to_retrieved_chunk(isp_hit)
        assert _is_thread4_non_optichain(chunk) is False

    def test_thread4_appears_in_excluded_evidence_in_step04_bundle(self) -> None:
        """Thread 4 Slack chunks must be in excluded_evidence, not admitted_evidence."""
        t4_hit = _make_slack_chunk_dict(thread_id="T4")
        t1_hit = _make_slack_chunk_dict(thread_id="T1")
        pam_hit = _make_chunk_dict(source_id="PAM-001", chunk_id="PAM-001__row_A",
                                   source_name="PAM", source_type="STRUCTURED_TABLE", citation_label="PAM-001 A")

        retrievals: dict[str, RetrievalResult] = {
            "it_security_output": _make_direct_result(payload={"data_classification": "UNREGULATED", "fast_track_eligible": True}),
            "legal_output": _make_direct_result(payload={"dpa_required": False, "nda_status": "EXECUTED"}),
            "vendor_relationship": _make_direct_result(payload={"vendor_class": "CLASS_A", "deal_size": 50000}),
            "approval_matrix_rows": _make_retrieval_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
            "fast_track_rows": _make_retrieval_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
            "slack_procurement": _make_retrieval_result(
                source_id="SLK-001",
                output_name="slack_procurement",
                hits=[t4_hit, t1_hit],
            ),
        }

        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(retrievals, _admissible_validation())

        excluded_ids = [e.chunk.chunk_id for e in bundle.excluded_evidence]
        admitted_ids = [c.chunk_id for c in bundle.admitted_evidence]

        assert "SLK-001__thread_T4" in excluded_ids, "Thread 4 must be in excluded_evidence"
        assert "SLK-001__thread_T4" not in admitted_ids, "Thread 4 must not be in admitted_evidence"
        assert "SLK-001__thread_T1" in admitted_ids, "Thread 1 should be admitted"

    def test_thread4_exclusion_reason_is_informative(self) -> None:
        """The exclusion reason for Thread 4 must clearly identify the cause."""
        t4_hit = _make_slack_chunk_dict(thread_id="T4")
        pam_hit = _make_chunk_dict(source_id="PAM-001", chunk_id="PAM-001__row_A",
                                   source_name="PAM", source_type="STRUCTURED_TABLE", citation_label="PAM-001 A")

        retrievals: dict[str, RetrievalResult] = {
            "it_security_output": _make_direct_result(payload={}),
            "legal_output": _make_direct_result(payload={}),
            "vendor_relationship": _make_direct_result(payload={}),
            "approval_matrix_rows": _make_retrieval_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
            "fast_track_rows": _make_retrieval_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
            "slack_procurement": _make_retrieval_result(
                source_id="SLK-001",
                output_name="slack_procurement",
                hits=[t4_hit],
            ),
        }

        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(retrievals, _admissible_validation())

        t4_exclusions = [
            e for e in bundle.excluded_evidence
            if e.chunk.chunk_id == "SLK-001__thread_T4"
        ]
        assert len(t4_exclusions) == 1
        assert "non_optichain" in t4_exclusions[0].exclusion_reason


# ---------------------------------------------------------------------------
# Tests: Permission-denied exclusion flows through bundle assembly
# ---------------------------------------------------------------------------


class TestPermissionDeniedInBundle:
    def test_permission_denied_item_recorded_as_excluded_chunk(self) -> None:
        """When the router returns an excluded_item for a permission denial,
        the bundle assembler must surface it as an ExcludedChunk."""
        pam_hit = _make_chunk_dict(source_id="PAM-001", chunk_id="PAM-001__row_A",
                                   source_name="PAM", source_type="STRUCTURED_TABLE", citation_label="PAM-001 A")
        # Simulate a result where SLK-001 was denied (router returned excluded_items)
        denied_slack_result = RetrievalResult(
            request=RetrievalRequest(
                request_id="TEST-DENIED",
                lane=RetrievalLane.INDEXED_HYBRID,
                source_id="SLK-001",
                access_role="it_security",
                output_name="slack_procurement",
            ),
            payload=[],
            admitted_items=[],
            excluded_items=[
                {
                    "source_id": "SLK-001",
                    "reason": "'it_security' is not permitted to query SLK-001.",
                    "access_role": "it_security",
                }
            ],
            retrieved_chunks=[],
        )

        retrievals: dict[str, RetrievalResult] = {
            "it_security_output": _make_direct_result(payload={}),
            "legal_output": _make_direct_result(payload={}),
            "vendor_relationship": _make_direct_result(payload={}),
            "approval_matrix_rows": _make_retrieval_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
            "fast_track_rows": _make_retrieval_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
            "slack_procurement": denied_slack_result,
        }

        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(retrievals, _admissible_validation())

        assert len(bundle.excluded_evidence) >= 1
        reasons = [e.exclusion_reason for e in bundle.excluded_evidence]
        assert any("not permitted" in r for r in reasons)


# ---------------------------------------------------------------------------
# Tests: Provenance and citation labels
# ---------------------------------------------------------------------------


class TestProvenanceAndCitationLabels:
    def test_isp_chunks_have_citation_labels(self) -> None:
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = _make_chunk_dict(chunk_id="ISP-001__section_12", citation_label="ISP-001 §12")
        chunk = _chunk_dict_to_retrieved_chunk(hit)
        assert chunk.citation_label == "ISP-001 §12"

    def test_bundle_source_provenance_lists_queried_sources(self) -> None:
        assembler = BundleAssembler()
        retrievals = _minimal_step02_retrievals()
        bundle = assembler.assemble_step02(retrievals, _admissible_validation())

        source_ids = {p["source_id"] for p in bundle.source_provenance}
        assert "ISP-001" in source_ids
        assert "VQ-OC-001" in source_ids

    def test_chunk_citation_label_from_chunk_json(self) -> None:
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = _make_chunk_dict(
            source_id="PAM-001",
            chunk_id="PAM-001__row_A-T1",
            citation_label="PAM-001 row A-T1",
            source_type="STRUCTURED_TABLE",
        )
        chunk = _chunk_dict_to_retrieved_chunk(hit)
        assert chunk.citation_label == "PAM-001 row A-T1"
