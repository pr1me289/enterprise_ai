"""Comprehensive tests for bundle assembly, admissibility enforcement, and BundleValidator.

Covers:
- Each step's bundle includes only sources allowed for that step's agent
- Tier-3 sources never produce is_primary_citable=True chunks in admitted_evidence
- Matrix rows (DPA, PAM) appear in structured_fields, not as RetrievedChunks in admitted_evidence
- Policy citations have stable citation labels matching source_id + section/row pattern
- admissibility_status is correct under different evidence scenarios:
    ADMISSIBLE, PARTIAL (missing fields), ESCALATION_REQUIRED (prohibited sources)
- BundleValidator correctly validates/rejects bundles
- Six demo requirements from the build prompt
"""

from __future__ import annotations

from typing import Any


from orchestration.models.contracts import BundleValidationResult, RetrievalRequest, RetrievalResult
from orchestration.models.enums import RetrievalLane
from orchestration.retrieval.bundle_assembler import BundleAssembler, _resolve_admissibility
from orchestration.validation.bundle_validator import ALLOWED_SOURCES, REQUIRED_FIELDS, BundleValidator


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    source_id: str = "ISP-001",
    chunk_id: str = "ISP-001__section_12",
    authority_tier: int = 1,
    is_primary_citable: bool = True,
    citation_label: str = "ISP-001 §12",
    source_name: str = "IT Security Policy",
    source_type: str = "POLICY_DOCUMENT",
    text: str = "Policy text.",
    **extra: Any,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "source_id": source_id,
        "source_name": source_name,
        "source_type": source_type,
        "chunk_id": chunk_id,
        "authority_tier": authority_tier,
        "retrieval_lane": "indexed_hybrid",
        "is_primary_citable": is_primary_citable,
        "text": text,
        "citation_label": citation_label,
    }
    d.update(extra)
    return d


def _make_slack_chunk(
    thread_id: str = "T1",
    is_primary_citable: bool = False,
    domain_scope: str | None = None,
) -> dict[str, Any]:
    extra: dict[str, Any] = {"thread_id": thread_id}
    if domain_scope is not None:
        extra["domain_scope"] = domain_scope
    return _make_chunk(
        source_id="SLK-001",
        source_name="Slack / Meeting Thread Notes",
        source_type="SLACK_THREAD",
        chunk_id=f"SLK-001__thread_{thread_id}",
        authority_tier=3,
        is_primary_citable=is_primary_citable,
        citation_label=f"SLK-001 thread {thread_id}",
        text=f"Slack thread {thread_id} text.",
        **extra,
    )


def _make_indexed_result(
    source_id: str = "ISP-001",
    output_name: str = "policy_chunks",
    hits: list[dict[str, Any]] | None = None,
    excluded_items: list[dict[str, Any]] | None = None,
) -> RetrievalResult:
    from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

    hits = hits or []
    typed_chunks = [_chunk_dict_to_retrieved_chunk(h) for h in hits]
    return RetrievalResult(
        request=RetrievalRequest(
            request_id="TEST-IDX",
            lane=RetrievalLane.INDEXED_HYBRID,
            source_id=source_id,
            access_role="procurement",
            output_name=output_name,
        ),
        payload=hits,
        admitted_items=hits,
        excluded_items=excluded_items or [],
        retrieved_chunks=typed_chunks,
    )


def _make_direct_result(
    source_id: str = "VQ-OC-001",
    output_name: str = "field",
    payload: dict[str, Any] | None = None,
) -> RetrievalResult:
    payload = payload or {}
    return RetrievalResult(
        request=RetrievalRequest(
            request_id="TEST-DS",
            lane=RetrievalLane.DIRECT_STRUCTURED,
            source_id=source_id,
            access_role="it_security",
            output_name=output_name,
            field_map={k: (k,) for k in payload},
        ),
        payload=payload,
        admitted_items=[{"field_path": k, "value_present": True} for k in payload],
    )


def _admissible_validation() -> dict[str, Any]:
    return {"admissible": True, "missing_fields": [], "prohibited_sources": []}


def _partial_validation(missing: list[str] | None = None) -> dict[str, Any]:
    return {"admissible": False, "missing_fields": missing or ["some_field"], "prohibited_sources": []}


def _escalation_validation(prohibited: list[str] | None = None) -> dict[str, Any]:
    return {
        "admissible": False,
        "missing_fields": [],
        "prohibited_sources": prohibited or ["FORBIDDEN-001"],
    }


def _minimal_step02_retrievals() -> dict[str, RetrievalResult]:
    isp_hit = _make_chunk(chunk_id="ISP-001__section_12", citation_label="ISP-001 §12")
    return {
        "integration_inputs": _make_direct_result(payload={"integration_details.erp_type": "EXPORT_ONLY"}),
        "classification_inputs": _make_direct_result(payload={"data_classification_self_reported": False}),
        "eu_inputs": _make_direct_result(payload={"eu_personal_data_flag": False}),
        "nda_inputs": _make_direct_result(payload={"existing_nda_status": "EXECUTED"}),
        "erp_tier_policy_chunks": _make_indexed_result(source_id="ISP-001", output_name="erp_tier_policy_chunks", hits=[isp_hit]),
        "classification_policy_chunks": _make_indexed_result(source_id="ISP-001", output_name="classification_policy_chunks", hits=[isp_hit]),
        "fast_track_policy_chunks": _make_indexed_result(source_id="ISP-001", output_name="fast_track_policy_chunks", hits=[isp_hit]),
        "nda_policy_chunks": _make_indexed_result(source_id="ISP-001", output_name="nda_policy_chunks", hits=[isp_hit]),
    }


def _minimal_step03_retrievals() -> dict[str, RetrievalResult]:
    isp_hit = _make_chunk(chunk_id="ISP-001__section_12", citation_label="ISP-001 §12")
    dpa_row = _make_chunk(
        source_id="DPA-TM-001",
        chunk_id="DPA-TM-001__row_EU-001",
        citation_label="DPA-TM-001 row EU-001",
        source_name="DPA Legal Trigger Matrix",
        source_type="LEGAL_TRIGGER_MATRIX",
        row_id="EU-001",
    )
    return {
        "upstream_security": _make_direct_result(
            source_id="STEP-02",
            payload={
                "upstream_data_classification": "UNREGULATED",
                "status": "complete",
                "policy_citations": [],
            },
        ),
        "eu_inputs": _make_direct_result(payload={"eu_personal_data_flag": False, "data_subjects_eu": False}),
        "nda_inputs": _make_direct_result(payload={"existing_nda_status": "EXECUTED"}),
        "dpa_status": _make_direct_result(payload={"dpa_required": False}),
        "dpa_trigger_rows": _make_direct_result(
            source_id="DPA-TM-001",
            payload={"rows": [dpa_row]},
        ),
        "nda_clause_chunks": _make_indexed_result(source_id="ISP-001", output_name="nda_clause_chunks", hits=[isp_hit]),
    }


def _minimal_step04_retrievals() -> dict[str, RetrievalResult]:
    pam_hit = _make_chunk(
        source_id="PAM-001",
        chunk_id="PAM-001__row_A-T3",
        citation_label="PAM-001 row A-T3",
        source_name="Procurement Approval Matrix",
        source_type="PROCUREMENT_APPROVAL_MATRIX",
        row_id="A-T3",
    )
    return {
        "it_security_output": _make_direct_result(
            source_id="STEP-02",
            payload={"data_classification": "UNREGULATED", "fast_track_eligible": True, "integration_tier": "TIER_3"},
        ),
        "legal_output": _make_direct_result(
            source_id="STEP-03",
            payload={"dpa_required": False, "dpa_blocker": False, "nda_status": "EXECUTED", "nda_blocker": False},
        ),
        "vendor_relationship": _make_direct_result(
            source_id="VQ-OC-001",
            payload={"vendor_class": "CLASS_A", "deal_size": 50000},
        ),
        "approval_matrix_rows": _make_indexed_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
        "fast_track_rows": _make_indexed_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
        "slack_procurement": _make_indexed_result(source_id="SLK-001", output_name="slack_procurement", hits=[]),
    }


# ---------------------------------------------------------------------------
# Tests: _resolve_admissibility helper
# ---------------------------------------------------------------------------


class TestResolveAdmissibility:
    def test_admissible_true_returns_admissible(self) -> None:
        assert _resolve_admissibility({"admissible": True, "prohibited_sources": []}) == "ADMISSIBLE"

    def test_admissible_false_no_prohibited_returns_partial(self) -> None:
        assert _resolve_admissibility({"admissible": False, "prohibited_sources": []}) == "PARTIAL"

    def test_admissible_false_with_prohibited_returns_escalation_required(self) -> None:
        assert _resolve_admissibility({"admissible": False, "prohibited_sources": ["FORBIDDEN-001"]}) == "ESCALATION_REQUIRED"

    def test_empty_validation_returns_partial(self) -> None:
        # No admissible key, no prohibited_sources → PARTIAL
        assert _resolve_admissibility({}) == "PARTIAL"

    def test_admissible_true_with_prohibited_still_admissible(self) -> None:
        # admissible flag takes priority when True — the caller should never set this
        # combination, but if they do, ADMISSIBLE wins (assembler trusts the validator).
        assert _resolve_admissibility({"admissible": True, "prohibited_sources": ["X"]}) == "ADMISSIBLE"


# ---------------------------------------------------------------------------
# Tests: BundleValidator
# ---------------------------------------------------------------------------


class TestBundleValidator:
    def _validator(self) -> BundleValidator:
        return BundleValidator()

    def test_step02_admissible_with_all_required_fields(self) -> None:
        v = self._validator()
        present = {
            "integration_details.erp_type",
            "data_classification_self_reported",
            "regulated_data_types",
            "eu_personal_data_flag",
            "data_subjects_eu",
            "existing_nda_status",
        }
        result = v.validate(step_id="STEP-02", source_ids=["VQ-OC-001", "ISP-001"], present_fields=present, missing_fields=[])
        assert result.admissible is True
        assert result.prohibited_sources == []
        assert result.missing_fields == []
        assert result.escalation_required is False

    def test_step02_partial_when_field_missing(self) -> None:
        v = self._validator()
        result = v.validate(
            step_id="STEP-02",
            source_ids=["VQ-OC-001", "ISP-001"],
            present_fields={"integration_details.erp_type"},  # Missing other required fields
            missing_fields=[],
        )
        assert result.admissible is False
        assert result.escalation_required is False
        assert len(result.missing_fields) > 0

    def test_prohibited_source_sets_escalation_required(self) -> None:
        v = self._validator()
        result = v.validate(
            step_id="STEP-02",
            source_ids=["VQ-OC-001", "ISP-001", "SLK-001"],  # SLK-001 not allowed at STEP-02
            present_fields={"integration_details.erp_type"},
            missing_fields=[],
        )
        assert result.admissible is False
        assert result.escalation_required is True
        assert "SLK-001" in result.prohibited_sources

    def test_dpa_not_allowed_at_step02(self) -> None:
        v = self._validator()
        result = v.validate(
            step_id="STEP-02",
            source_ids=["VQ-OC-001", "ISP-001", "DPA-TM-001"],
            present_fields=set(REQUIRED_FIELDS["STEP-02"]),
            missing_fields=[],
        )
        assert result.escalation_required is True
        assert "DPA-TM-001" in result.prohibited_sources

    def test_pam_only_allowed_at_step04(self) -> None:
        v = self._validator()
        # PAM-001 is allowed at STEP-04 but not STEP-02
        result_02 = v.validate(
            step_id="STEP-02",
            source_ids=["PAM-001"],
            present_fields=set(REQUIRED_FIELDS["STEP-02"]),
            missing_fields=[],
        )
        assert "PAM-001" in result_02.prohibited_sources

        result_04 = v.validate(
            step_id="STEP-04",
            source_ids=["STEP-02", "STEP-03", "VQ-OC-001", "PAM-001", "SLK-001"],
            present_fields=set(REQUIRED_FIELDS["STEP-04"]),
            missing_fields=[],
        )
        assert result_04.prohibited_sources == []

    def test_slack_only_allowed_at_step04(self) -> None:
        v = self._validator()
        # SLK-001 is allowed at STEP-04 but not STEP-02 or STEP-03
        for step_id in ("STEP-02", "STEP-03", "STEP-05", "STEP-06"):
            result = v.validate(
                step_id=step_id,
                source_ids=["SLK-001"],
                present_fields=set(),
                missing_fields=[],
            )
            assert "SLK-001" in result.prohibited_sources, f"SLK-001 should be prohibited at {step_id}"

    def test_step06_allowed_sources(self) -> None:
        v = self._validator()
        result = v.validate(
            step_id="STEP-06",
            source_ids=list(ALLOWED_SOURCES["STEP-06"]),
            present_fields=set(REQUIRED_FIELDS["STEP-06"]),
            missing_fields=[],
        )
        assert result.admissible is True
        assert result.prohibited_sources == []

    def test_missing_fields_from_param_merged_with_required(self) -> None:
        v = self._validator()
        result = v.validate(
            step_id="STEP-02",
            source_ids=["VQ-OC-001", "ISP-001"],
            present_fields=set(REQUIRED_FIELDS["STEP-02"]),
            missing_fields=["extra_missing_field"],
        )
        assert "extra_missing_field" in result.missing_fields
        assert result.admissible is False

    def test_step04_required_fields_present(self) -> None:
        v = self._validator()
        result = v.validate(
            step_id="STEP-04",
            source_ids=list(ALLOWED_SOURCES["STEP-04"]),
            present_fields=set(REQUIRED_FIELDS["STEP-04"]),
            missing_fields=[],
        )
        assert result.admissible is True
        assert result.escalation_required is False

    def test_unknown_step_id_treats_all_sources_as_prohibited(self) -> None:
        v = self._validator()
        result = v.validate(
            step_id="STEP-99",
            source_ids=["ISP-001"],
            present_fields=set(),
            missing_fields=[],
        )
        assert "ISP-001" in result.prohibited_sources
        assert result.escalation_required is True


# ---------------------------------------------------------------------------
# Tests: admissibility_status in ContextBundle via BundleAssembler
# ---------------------------------------------------------------------------


class TestAdmissibilityStatus:
    def test_step02_admissible_status(self) -> None:
        assembler = BundleAssembler()
        bundle = assembler.assemble_step02(_minimal_step02_retrievals(), _admissible_validation())
        assert bundle.admissibility_status == "ADMISSIBLE"

    def test_step02_partial_status_when_missing_fields(self) -> None:
        assembler = BundleAssembler()
        bundle = assembler.assemble_step02(_minimal_step02_retrievals(), _partial_validation(["eu_personal_data_flag"]))
        assert bundle.admissibility_status == "PARTIAL"

    def test_step02_escalation_required_when_prohibited_sources(self) -> None:
        assembler = BundleAssembler()
        bundle = assembler.assemble_step02(_minimal_step02_retrievals(), _escalation_validation(["SLK-001"]))
        assert bundle.admissibility_status == "ESCALATION_REQUIRED"

    def test_step03_admissible_status(self) -> None:
        assembler = BundleAssembler()
        bundle = assembler.assemble_step03(_minimal_step03_retrievals(), _admissible_validation())
        assert bundle.admissibility_status == "ADMISSIBLE"

    def test_step03_escalation_required_when_prohibited_sources(self) -> None:
        assembler = BundleAssembler()
        bundle = assembler.assemble_step03(_minimal_step03_retrievals(), _escalation_validation(["PAM-001"]))
        assert bundle.admissibility_status == "ESCALATION_REQUIRED"

    def test_step04_admissible_status(self) -> None:
        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(_minimal_step04_retrievals(), _admissible_validation())
        assert bundle.admissibility_status == "ADMISSIBLE"

    def test_step04_partial_when_missing_fields(self) -> None:
        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(_minimal_step04_retrievals(), _partial_validation(["dpa_required"]))
        assert bundle.admissibility_status == "PARTIAL"

    def test_step04_escalation_required_when_prohibited_sources(self) -> None:
        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(_minimal_step04_retrievals(), _escalation_validation(["DPA-TM-001"]))
        assert bundle.admissibility_status == "ESCALATION_REQUIRED"


# ---------------------------------------------------------------------------
# Tests: Source authority — Tier-3 never primary-citable in admitted_evidence
# ---------------------------------------------------------------------------


class TestTier3NeverPrimaryCitable:
    def test_slack_chunk_is_never_primary_citable_in_step04_bundle(self) -> None:
        slack_hit_primary = _make_slack_chunk(thread_id="T1", is_primary_citable=True)
        pam_hit = _make_chunk(
            source_id="PAM-001",
            chunk_id="PAM-001__row_A",
            source_name="Procurement Approval Matrix",
            source_type="STRUCTURED_TABLE",
            citation_label="PAM-001 row A",
        )
        retrievals: dict[str, RetrievalResult] = {
            "it_security_output": _make_direct_result(payload={"data_classification": "UNREGULATED", "fast_track_eligible": True, "integration_tier": "TIER_3"}),
            "legal_output": _make_direct_result(payload={"dpa_required": False, "dpa_blocker": False, "nda_status": "EXECUTED", "nda_blocker": False}),
            "vendor_relationship": _make_direct_result(payload={"vendor_class": "CLASS_A", "deal_size": 50000}),
            "approval_matrix_rows": _make_indexed_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
            "fast_track_rows": _make_indexed_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
            "slack_procurement": _make_indexed_result(source_id="SLK-001", output_name="slack_procurement", hits=[slack_hit_primary]),
        }
        bundle = BundleAssembler().assemble_step04(retrievals, _admissible_validation())
        slack_chunks = [c for c in bundle.admitted_evidence if c.source_id == "SLK-001"]
        assert len(slack_chunks) == 1
        assert slack_chunks[0].is_primary_citable is False

    def test_tier3_pvd_chunk_not_primary_citable_forced(self) -> None:
        """Any Tier-3 source (e.g., PVD-001) should not be primary-citable.
        The source_contract defines PVD-001 is_primary_citable=False already, so
        no chunk from PVD-001 should ever arrive with is_primary_citable=True.
        This test validates that if one does slip through, the Slack rule only
        covers SLK-001, so we document that PVD-001 would need its own rule."""
        from preprocessing.source_contract import SOURCE_CONTRACTS_BY_ID

        pvd = SOURCE_CONTRACTS_BY_ID["PVD-001"]
        slk = SOURCE_CONTRACTS_BY_ID["SLK-001"]
        assert pvd.is_primary_citable is False
        assert slk.is_primary_citable is False
        assert pvd.authority_tier == 3
        assert slk.authority_tier == 3

    def test_tier1_isp_chunk_is_primary_citable(self) -> None:
        """Tier-1 sources (ISP-001) must retain is_primary_citable=True."""
        assembler = BundleAssembler()
        bundle = assembler.assemble_step02(_minimal_step02_retrievals(), _admissible_validation())
        isp_chunks = [c for c in bundle.admitted_evidence if c.source_id == "ISP-001"]
        assert len(isp_chunks) > 0
        assert all(c.is_primary_citable is True for c in isp_chunks)


# ---------------------------------------------------------------------------
# Tests: Matrix rows in structured_fields (DPA, PAM)
# ---------------------------------------------------------------------------


class TestMatrixRowsInStructuredFields:
    def test_step03_dpa_trigger_rows_in_structured_fields(self) -> None:
        """DPA trigger matrix rows must appear in structured_fields, not admitted_evidence."""
        assembler = BundleAssembler()
        bundle = assembler.assemble_step03(_minimal_step03_retrievals(), _admissible_validation())

        assert "dpa_trigger_rows" in bundle.structured_fields
        # DPA rows are from DIRECT_STRUCTURED lane — they do NOT appear in admitted_evidence
        dpa_chunks_in_evidence = [c for c in bundle.admitted_evidence if c.source_id == "DPA-TM-001"]
        assert len(dpa_chunks_in_evidence) == 0, "DPA matrix rows must not appear in admitted_evidence"

    def test_step04_approval_matrix_rows_accessible(self) -> None:
        """PAM approval matrix rows must appear in structured_fields."""
        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(_minimal_step04_retrievals(), _admissible_validation())

        assert "approval_path_matrix_rows" in bundle.structured_fields

    def test_step04_fast_track_rows_accessible(self) -> None:
        """PAM fast-track routing rows must appear in structured_fields."""
        assembler = BundleAssembler()
        bundle = assembler.assemble_step04(_minimal_step04_retrievals(), _admissible_validation())

        assert "fast_track_routing_rows" in bundle.structured_fields

    def test_step04_pam_chunks_from_indexed_are_in_admitted_evidence(self) -> None:
        """PAM-001 chunks retrieved via INDEXED_HYBRID lane appear in admitted_evidence."""
        pam_hit = _make_chunk(
            source_id="PAM-001",
            chunk_id="PAM-001__row_A-T3",
            citation_label="PAM-001 row A-T3",
            source_name="Procurement Approval Matrix",
            source_type="STRUCTURED_TABLE",
        )
        retrievals = _minimal_step04_retrievals()
        # Override with an indexed result that has a PAM hit
        retrievals["approval_matrix_rows"] = _make_indexed_result(
            source_id="PAM-001",
            output_name="approval_matrix_rows",
            hits=[pam_hit],
        )
        bundle = BundleAssembler().assemble_step04(retrievals, _admissible_validation())

        pam_admitted = [c for c in bundle.admitted_evidence if c.source_id == "PAM-001"]
        assert len(pam_admitted) >= 1


# ---------------------------------------------------------------------------
# Tests: Policy section citation labels are stable
# ---------------------------------------------------------------------------


class TestPolicyCitationLabels:
    def test_isp_chunk_citation_label_stable(self) -> None:
        hit = _make_chunk(
            chunk_id="ISP-001__section_12",
            citation_label="ISP-001 §12",
            section_id="12",
        )
        retrievals = _minimal_step02_retrievals()
        retrievals["erp_tier_policy_chunks"] = _make_indexed_result(
            source_id="ISP-001",
            output_name="erp_tier_policy_chunks",
            hits=[hit],
        )
        retrievals["classification_policy_chunks"] = _make_indexed_result(
            source_id="ISP-001", output_name="classification_policy_chunks", hits=[hit]
        )
        retrievals["fast_track_policy_chunks"] = _make_indexed_result(
            source_id="ISP-001", output_name="fast_track_policy_chunks", hits=[hit]
        )
        retrievals["nda_policy_chunks"] = _make_indexed_result(
            source_id="ISP-001", output_name="nda_policy_chunks", hits=[hit]
        )
        bundle = BundleAssembler().assemble_step02(retrievals, _admissible_validation())

        isp_chunks = [c for c in bundle.admitted_evidence if c.source_id == "ISP-001"]
        assert len(isp_chunks) > 0
        for c in isp_chunks:
            assert c.citation_label == "ISP-001 §12"

    def test_pam_row_citation_label_contains_row_id(self) -> None:
        """PAM matrix rows should have citation labels that include the row ID."""
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = _make_chunk(
            source_id="PAM-001",
            chunk_id="PAM-001__row_A-T3",
            citation_label="PAM-001 row A-T3",
            source_type="STRUCTURED_TABLE",
            row_id="A-T3",
        )
        chunk = _chunk_dict_to_retrieved_chunk(hit)
        assert "PAM-001" in chunk.citation_label
        assert "A-T3" in chunk.citation_label

    def test_dpa_row_citation_label_contains_row_id(self) -> None:
        """DPA trigger matrix rows should have citation labels that include the row ID."""
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = _make_chunk(
            source_id="DPA-TM-001",
            chunk_id="DPA-TM-001__row_EU-001",
            citation_label="DPA-TM-001 row EU-001",
            source_type="LEGAL_TRIGGER_MATRIX",
            row_id="EU-001",
        )
        chunk = _chunk_dict_to_retrieved_chunk(hit)
        assert "DPA-TM-001" in chunk.citation_label
        assert "EU-001" in chunk.citation_label

    def test_citation_label_falls_back_to_chunk_id_when_absent(self) -> None:
        """If citation_label is not in the chunk dict, chunk_id is used as fallback."""
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = {
            "source_id": "ISP-001",
            "source_name": "IT Security Policy",
            "source_type": "POLICY_DOCUMENT",
            "chunk_id": "ISP-001__section_17",
            "authority_tier": 1,
            "retrieval_lane": "indexed_hybrid",
            "is_primary_citable": True,
            "text": "Some policy text.",
            # No citation_label key
        }
        chunk = _chunk_dict_to_retrieved_chunk(hit)
        assert chunk.citation_label == "ISP-001__section_17"


# ---------------------------------------------------------------------------
# Tests: Thread 4 exclusion (Demo requirement 1)
# ---------------------------------------------------------------------------


class TestThread4ExclusionDemoRequirement:
    def test_thread4_excluded_from_optichain_step04_bundle(self) -> None:
        """Build prompt demo requirement: Thread 4 in Slack is excluded from OptiChain determinations."""
        t4_hit = _make_slack_chunk(thread_id="T4")
        t1_hit = _make_slack_chunk(thread_id="T1")
        pam_hit = _make_chunk(
            source_id="PAM-001",
            chunk_id="PAM-001__row_A",
            source_name="PAM",
            source_type="STRUCTURED_TABLE",
            citation_label="PAM-001 A",
        )
        retrievals: dict[str, RetrievalResult] = {
            "it_security_output": _make_direct_result(payload={"data_classification": "UNREGULATED", "fast_track_eligible": True, "integration_tier": "TIER_3"}),
            "legal_output": _make_direct_result(payload={"dpa_required": False, "dpa_blocker": False, "nda_status": "EXECUTED", "nda_blocker": False}),
            "vendor_relationship": _make_direct_result(payload={"vendor_class": "CLASS_A", "deal_size": 50000}),
            "approval_matrix_rows": _make_indexed_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
            "fast_track_rows": _make_indexed_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
            "slack_procurement": _make_indexed_result(source_id="SLK-001", output_name="slack_procurement", hits=[t4_hit, t1_hit]),
        }
        bundle = BundleAssembler().assemble_step04(retrievals, _admissible_validation())

        admitted_ids = {c.chunk_id for c in bundle.admitted_evidence}
        excluded_ids = {e.chunk.chunk_id for e in bundle.excluded_evidence}

        assert "SLK-001__thread_T4" not in admitted_ids, "Thread 4 must NOT be admitted"
        assert "SLK-001__thread_T4" in excluded_ids, "Thread 4 must be in excluded_evidence"
        assert "SLK-001__thread_T1" in admitted_ids, "Thread 1 should be admitted"

    def test_thread4_exclusion_reason_is_informative(self) -> None:
        t4_hit = _make_slack_chunk(thread_id="T4")
        pam_hit = _make_chunk(source_id="PAM-001", chunk_id="PAM-001__row_A",
                               source_name="PAM", source_type="STRUCTURED_TABLE", citation_label="PAM-001 A")
        retrievals: dict[str, RetrievalResult] = {
            "it_security_output": _make_direct_result(payload={}),
            "legal_output": _make_direct_result(payload={}),
            "vendor_relationship": _make_direct_result(payload={}),
            "approval_matrix_rows": _make_indexed_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
            "fast_track_rows": _make_indexed_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
            "slack_procurement": _make_indexed_result(source_id="SLK-001", output_name="slack_procurement", hits=[t4_hit]),
        }
        bundle = BundleAssembler().assemble_step04(retrievals, _admissible_validation())

        t4_excluded = [e for e in bundle.excluded_evidence if e.chunk.chunk_id == "SLK-001__thread_T4"]
        assert len(t4_excluded) == 1
        assert "non_optichain" in t4_excluded[0].exclusion_reason


# ---------------------------------------------------------------------------
# Tests: Slack supplementary only (Demo requirement 2)
# ---------------------------------------------------------------------------


class TestSlackSupplementaryOnlyDemoRequirement:
    def test_slack_is_never_primary_evidence_in_bundle(self) -> None:
        """Build prompt demo requirement: Slack is supplementary only and never primary evidence."""
        slack_hit = _make_slack_chunk(thread_id="T2", is_primary_citable=True)
        pam_hit = _make_chunk(source_id="PAM-001", chunk_id="PAM-001__row_A",
                               source_name="PAM", source_type="STRUCTURED_TABLE", citation_label="PAM-001 A")
        retrievals: dict[str, RetrievalResult] = {
            "it_security_output": _make_direct_result(payload={"data_classification": "UNREGULATED", "fast_track_eligible": True, "integration_tier": "TIER_3"}),
            "legal_output": _make_direct_result(payload={"dpa_required": False, "dpa_blocker": False, "nda_status": "EXECUTED", "nda_blocker": False}),
            "vendor_relationship": _make_direct_result(payload={"vendor_class": "CLASS_A", "deal_size": 50000}),
            "approval_matrix_rows": _make_indexed_result(source_id="PAM-001", output_name="approval_matrix_rows", hits=[pam_hit]),
            "fast_track_rows": _make_indexed_result(source_id="PAM-001", output_name="fast_track_rows", hits=[pam_hit]),
            "slack_procurement": _make_indexed_result(source_id="SLK-001", output_name="slack_procurement", hits=[slack_hit]),
        }
        bundle = BundleAssembler().assemble_step04(retrievals, _admissible_validation())

        slack_chunks = [c for c in bundle.admitted_evidence if c.source_id == "SLK-001"]
        assert len(slack_chunks) == 1
        # Must be forced to supplementary (is_primary_citable=False)
        assert slack_chunks[0].is_primary_citable is False

    def test_slack_authority_tier_is_3(self) -> None:
        """SLK-001 must have authority_tier=3 per source_contract."""
        from preprocessing.source_contract import SOURCE_CONTRACTS_BY_ID
        slk = SOURCE_CONTRACTS_BY_ID["SLK-001"]
        assert slk.authority_tier == 3
        assert slk.is_primary_citable is False


# ---------------------------------------------------------------------------
# Tests: Structured questionnaire facts passed through cleanly (Demo requirement 3)
# ---------------------------------------------------------------------------


class TestQuestionnaireFacts:
    def test_step02_questionnaire_fields_in_structured_fields(self) -> None:
        """Build prompt demo requirement: structured questionnaire facts are passed through cleanly."""
        assembler = BundleAssembler()
        bundle = assembler.assemble_step02(_minimal_step02_retrievals(), _admissible_validation())

        q = bundle.structured_fields.get("questionnaire", {})
        assert "integration_details.erp_type" in q, "ERP type must be present in questionnaire"
        assert "eu_personal_data_flag" in q
        assert "existing_nda_status" in q

    def test_step02_questionnaire_values_are_not_mangled(self) -> None:
        """Values from the questionnaire must pass through unchanged."""
        assembler = BundleAssembler()
        bundle = assembler.assemble_step02(_minimal_step02_retrievals(), _admissible_validation())

        q = bundle.structured_fields["questionnaire"]
        assert q["integration_details.erp_type"] == "EXPORT_ONLY"
        assert q["eu_personal_data_flag"] is False
        assert q["existing_nda_status"] == "EXECUTED"


# ---------------------------------------------------------------------------
# Tests: Matrix rows as atomic rule-table evidence (Demo requirement 4)
# ---------------------------------------------------------------------------


class TestMatrixRowsAtomicEvidence:
    def test_dpa_rows_atomic_in_step03_structured_fields(self) -> None:
        """Build prompt demo requirement: matrix rows are retrieved as atomic rule-table evidence."""
        dpa_row = {
            "row_id": "EU-001",
            "trigger_condition": "EU personal data present",
            "determination": "DPA required",
        }
        retrievals = _minimal_step03_retrievals()
        # Override dpa_trigger_rows with a direct result containing the atomic row
        retrievals["dpa_trigger_rows"] = _make_direct_result(
            source_id="DPA-TM-001",
            payload={"rows": [dpa_row]},
        )
        bundle = BundleAssembler().assemble_step03(retrievals, _admissible_validation())

        dpa_rows_field = bundle.structured_fields.get("dpa_trigger_rows", {})
        # The rows field should carry the atomic dict including row_id
        assert dpa_rows_field.get("rows") is not None
        assert dpa_rows_field["rows"][0]["row_id"] == "EU-001"

    def test_pam_rows_atomic_in_step04_structured_fields(self) -> None:
        """PAM approval matrix rows must be passed through as-is (atomic)."""
        pam_row = {
            "row_id": "A-T3",
            "vendor_class": "CLASS_A",
            "deal_size_usd_max": 100000,
            "approval_path": "FAST_TRACK",
        }
        retrievals = _minimal_step04_retrievals()
        # Simulate a DIRECT_STRUCTURED result for approval_matrix_rows
        retrievals["approval_matrix_rows"] = _make_direct_result(
            source_id="PAM-001",
            payload={"rows": [pam_row]},
        )
        bundle = BundleAssembler().assemble_step04(retrievals, _admissible_validation())

        pam_rows_field = bundle.structured_fields.get("approval_path_matrix_rows", {})
        assert pam_rows_field.get("rows") is not None
        assert pam_rows_field["rows"][0]["row_id"] == "A-T3"


# ---------------------------------------------------------------------------
# Tests: Policy sections with stable citation labels (Demo requirement 5)
# ---------------------------------------------------------------------------


class TestPolicySectionsCitationLabels:
    def test_isp_section_citation_label_format(self) -> None:
        """Build prompt demo requirement: policy sections are retrieved with stable citation labels."""
        hit = _make_chunk(
            chunk_id="ISP-001__section_17",
            citation_label="ISP-001 §17",
            section_id="17",
        )
        retrievals = _minimal_step02_retrievals()
        for key in ("erp_tier_policy_chunks", "classification_policy_chunks", "fast_track_policy_chunks", "nda_policy_chunks"):
            retrievals[key] = _make_indexed_result(source_id="ISP-001", output_name=key, hits=[hit])

        bundle = BundleAssembler().assemble_step02(retrievals, _admissible_validation())
        isp_chunks = [c for c in bundle.admitted_evidence if c.source_id == "ISP-001"]
        for c in isp_chunks:
            # Citation label must be "ISP-001 §17" not just the chunk_id
            assert c.citation_label == "ISP-001 §17"
            assert "ISP-001" in c.citation_label

    def test_section_id_in_extra_metadata_for_isp_chunks(self) -> None:
        """section_id must be preserved in extra_metadata for ISP-001 chunks."""
        from orchestration.retrieval.router import _chunk_dict_to_retrieved_chunk

        hit = _make_chunk(
            chunk_id="ISP-001__section_12",
            citation_label="ISP-001 §12",
            section_id="12",
            version="4.2",
        )
        chunk = _chunk_dict_to_retrieved_chunk(hit)
        assert chunk.extra_metadata.get("section_id") == "12"
        assert chunk.extra_metadata.get("version") == "4.2"


# ---------------------------------------------------------------------------
# Tests: Source-permission constraints per step (Demo requirement 6)
# ---------------------------------------------------------------------------


class TestSourcePermissionConstraintsPerStep:
    """Verify that each step only allows its expected sources, per source_contract.allowed_agents."""

    def test_step02_allowed_sources_match_source_contract(self) -> None:
        """STEP-02 agent is it_security_agent; ISP-001 and VQ-OC-001 are allowed."""
        from preprocessing.source_contract import SOURCE_CONTRACTS_BY_ID

        step02_agent = "it_security"
        # ISP-001 allows it_security
        assert step02_agent in SOURCE_CONTRACTS_BY_ID["ISP-001"].allowed_agents
        # VQ-OC-001 allows it_security
        assert step02_agent in SOURCE_CONTRACTS_BY_ID["VQ-OC-001"].allowed_agents
        # SLK-001 does NOT allow it_security
        assert step02_agent not in SOURCE_CONTRACTS_BY_ID["SLK-001"].allowed_agents
        # DPA-TM-001 does NOT allow it_security
        assert step02_agent not in SOURCE_CONTRACTS_BY_ID["DPA-TM-001"].allowed_agents
        # PAM-001 does NOT allow it_security
        assert step02_agent not in SOURCE_CONTRACTS_BY_ID["PAM-001"].allowed_agents

    def test_step03_allowed_sources_match_source_contract(self) -> None:
        """STEP-03 agent is legal_agent; DPA-TM-001, ISP-001, VQ-OC-001 are allowed."""
        from preprocessing.source_contract import SOURCE_CONTRACTS_BY_ID

        step03_agent = "legal"
        assert step03_agent in SOURCE_CONTRACTS_BY_ID["DPA-TM-001"].allowed_agents
        assert step03_agent in SOURCE_CONTRACTS_BY_ID["ISP-001"].allowed_agents
        assert step03_agent in SOURCE_CONTRACTS_BY_ID["VQ-OC-001"].allowed_agents
        # SLK-001 is NOT allowed for legal
        assert step03_agent not in SOURCE_CONTRACTS_BY_ID["SLK-001"].allowed_agents
        # PAM-001 is NOT allowed for legal
        assert step03_agent not in SOURCE_CONTRACTS_BY_ID["PAM-001"].allowed_agents

    def test_step04_allowed_sources_match_source_contract(self) -> None:
        """STEP-04 agent is procurement_agent; PAM-001, SLK-001, VQ-OC-001, ISP-001 allowed."""
        from preprocessing.source_contract import SOURCE_CONTRACTS_BY_ID

        step04_agent = "procurement"
        assert step04_agent in SOURCE_CONTRACTS_BY_ID["PAM-001"].allowed_agents
        assert step04_agent in SOURCE_CONTRACTS_BY_ID["SLK-001"].allowed_agents
        assert step04_agent in SOURCE_CONTRACTS_BY_ID["VQ-OC-001"].allowed_agents
        assert step04_agent in SOURCE_CONTRACTS_BY_ID["ISP-001"].allowed_agents
        # DPA-TM-001 is NOT allowed for procurement
        assert step04_agent not in SOURCE_CONTRACTS_BY_ID["DPA-TM-001"].allowed_agents

    def test_step05_vq_allowed_for_checklist_assembler(self) -> None:
        """STEP-05 agent is checklist_assembler; VQ-OC-001 is allowed, SLK-001 is not."""
        from preprocessing.source_contract import SOURCE_CONTRACTS_BY_ID

        step05_agent = "checklist_assembler"
        assert step05_agent in SOURCE_CONTRACTS_BY_ID["VQ-OC-001"].allowed_agents
        assert step05_agent not in SOURCE_CONTRACTS_BY_ID["SLK-001"].allowed_agents
        assert step05_agent not in SOURCE_CONTRACTS_BY_ID["DPA-TM-001"].allowed_agents

    def test_step06_vq_allowed_for_checkoff(self) -> None:
        """STEP-06 agent is checkoff; VQ-OC-001 and SHM-001 are allowed, SLK-001 is not."""
        from preprocessing.source_contract import SOURCE_CONTRACTS_BY_ID

        step06_agent = "checkoff"
        assert step06_agent in SOURCE_CONTRACTS_BY_ID["VQ-OC-001"].allowed_agents
        assert step06_agent in SOURCE_CONTRACTS_BY_ID["SHM-001"].allowed_agents
        assert step06_agent not in SOURCE_CONTRACTS_BY_ID["SLK-001"].allowed_agents
        assert step06_agent not in SOURCE_CONTRACTS_BY_ID["ISP-001"].allowed_agents

    def test_bundle_validator_allowed_sources_matches_step02(self) -> None:
        """BundleValidator ALLOWED_SOURCES for STEP-02 must include ISP-001 and VQ-OC-001."""
        assert "ISP-001" in ALLOWED_SOURCES["STEP-02"]
        assert "VQ-OC-001" in ALLOWED_SOURCES["STEP-02"]
        assert "SLK-001" not in ALLOWED_SOURCES["STEP-02"]
        assert "DPA-TM-001" not in ALLOWED_SOURCES["STEP-02"]

    def test_bundle_validator_allowed_sources_matches_step03(self) -> None:
        assert "DPA-TM-001" in ALLOWED_SOURCES["STEP-03"]
        assert "ISP-001" in ALLOWED_SOURCES["STEP-03"]
        assert "SLK-001" not in ALLOWED_SOURCES["STEP-03"]

    def test_bundle_validator_allowed_sources_matches_step04(self) -> None:
        assert "PAM-001" in ALLOWED_SOURCES["STEP-04"]
        assert "SLK-001" in ALLOWED_SOURCES["STEP-04"]
        assert "DPA-TM-001" not in ALLOWED_SOURCES["STEP-04"]

    def test_bundle_validator_allows_no_slack_outside_step04(self) -> None:
        """SLK-001 must only appear in STEP-04 allowed sources."""
        for step_id, allowed in ALLOWED_SOURCES.items():
            if step_id == "STEP-04":
                assert "SLK-001" in allowed, "SLK-001 must be allowed at STEP-04"
            else:
                assert "SLK-001" not in allowed, f"SLK-001 must NOT be allowed at {step_id}"


# ---------------------------------------------------------------------------
# Tests: BundleValidator escalation_required field on BundleValidationResult
# ---------------------------------------------------------------------------


class TestBundleValidationResultEscalationRequired:
    def test_escalation_required_false_when_admissible(self) -> None:
        v = BundleValidator()
        result = v.validate(
            step_id="STEP-02",
            source_ids=["VQ-OC-001", "ISP-001"],
            present_fields=set(REQUIRED_FIELDS["STEP-02"]),
            missing_fields=[],
        )
        assert result.escalation_required is False

    def test_escalation_required_false_when_only_missing_fields(self) -> None:
        v = BundleValidator()
        result = v.validate(
            step_id="STEP-02",
            source_ids=["VQ-OC-001", "ISP-001"],
            present_fields=set(),
            missing_fields=[],
        )
        assert result.escalation_required is False
        assert result.admissible is False

    def test_escalation_required_true_when_prohibited_source(self) -> None:
        v = BundleValidator()
        result = v.validate(
            step_id="STEP-02",
            source_ids=["VQ-OC-001", "ISP-001", "SLK-001"],
            present_fields=set(REQUIRED_FIELDS["STEP-02"]),
            missing_fields=[],
        )
        assert result.escalation_required is True
        assert result.admissible is False

    def test_bundle_validation_result_is_dataclass(self) -> None:
        result = BundleValidationResult(admissible=True)
        assert result.escalation_required is False
        assert result.missing_fields == []
        assert result.prohibited_sources == []
