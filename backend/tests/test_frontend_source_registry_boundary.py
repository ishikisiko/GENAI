from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_global_sources_page_uses_topic_registry_api_helpers():
    content = (_repo_root() / "src/pages/GlobalSourcesPage.tsx").read_text(encoding="utf-8")

    assert "fetchSourceTopics" in content
    assert "fetchSourceRegistry" in content
    assert "fetchSourceUsage" in content
    assert "createSourceTopicAssignment" in content
    assert "Unassigned" in content
    assert "Duplicate Candidates" in content
    assert "Stale Sources" in content


def test_documents_page_uses_grouped_case_source_selection_and_snapshot_api():
    content = (_repo_root() / "src/pages/DocumentsPage.tsx").read_text(encoding="utf-8")

    assert "fetchCaseSourceSelection" in content
    assert "attachGlobalSourceToCase" in content
    assert "sourceSelection?.sections" in content
    assert "sourceSelection?.semantic_recall" in content
    assert "matched_fragments" in content
    assert "ranking_reasons" in content
    assert "source.source_scope" in content
    assert "section.title" in content
    assert "section.description" in content
    assert "Manual Upload" in content
    assert ".from(\"source_documents\").insert(\n      selectedSources.map" not in content


def test_candidate_review_page_can_render_semantic_candidate_explanations():
    content = (_repo_root() / "src/pages/CandidateSourcesReviewPage.tsx").read_text(encoding="utf-8")

    assert "candidate.semantic_support" in content
    assert "candidate.matched_fragments" in content
    assert "candidate.ranking_reasons" in content
    assert "attachGlobalSourceToCase" in content
    assert "candidate.addToCaseDocuments" in content
