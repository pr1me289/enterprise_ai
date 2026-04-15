"""Test harness package for deterministic orchestration validation.

This harness exercises the full Supervisor pipeline with *mock* LLM and
indexed-retrieval adapters so every run is byte-deterministic and free.
It is the right tool for state-machine coverage, bundle admissibility
checks, and regression guards that should never depend on a live model.

For *real-LLM* validation of individual domain agents, handoff invariants,
and spec acceptance checks (A-01..A-07), see the pytest suite under:

    tests/unit/           — Layer 1: per-agent outputs
    tests/integration/    — Layer 2: cross-agent handoff invariants
    tests/acceptance/     — Layer 3: spec acceptance checks
    tests/full_pipeline/  — Layer 4: end-to-end real-API run

The real-LLM suite is gated on ``pytest.mark.api`` and is skipped unless
the user passes ``-m api`` with ``ANTHROPIC_API_KEY`` set. The two suites
are complementary — the harness keeps state-machine behavior honest,
while ``tests/`` keeps agent determinations honest.
"""
