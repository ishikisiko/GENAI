from __future__ import annotations

from backend.services.extraction_contracts import (
    DocumentGraphFragment,
    ExtractedClaim,
    ExtractedEntity,
    ExtractedRelation,
)
from backend.services.extraction_service import merge_document_graphs


def test_merge_document_graphs_preserves_first_entity_and_deduplicates_relations_and_claims():
    partials = [
        DocumentGraphFragment(
            source_doc_id="doc-1",
            entities=[
                ExtractedEntity(name="NutriPlus", entity_type="organization", description="Brand under review"),
                ExtractedEntity(name="Cold chain failure", entity_type="event", description="Logistics incident"),
            ],
            relations=[
                ExtractedRelation(
                    source_entity_name="NutriPlus",
                    target_entity_name="Cold chain failure",
                    relation_type="responded_to",
                    description="Initial response",
                )
            ],
            claims=[
                ExtractedClaim(
                    content="NutriPlus products spoiled in transit.",
                    claim_type="fact",
                    credibility="high",
                    source_doc_id="doc-1",
                )
            ],
        ),
        DocumentGraphFragment(
            source_doc_id="doc-2",
            entities=[
                ExtractedEntity(name=" nutriplus ", entity_type="organization", description="Duplicate casing variant"),
            ],
            relations=[
                ExtractedRelation(
                    source_entity_name="NutriPlus",
                    target_entity_name="Cold chain failure",
                    relation_type="responded_to",
                    description="Duplicate relation",
                )
            ],
            claims=[
                ExtractedClaim(
                    content="  NutriPlus products spoiled in transit. ",
                    claim_type="fact",
                    credibility="medium",
                    source_doc_id="doc-2",
                )
            ],
        ),
    ]

    merged = merge_document_graphs(partials)

    assert len(merged.entities) == 2
    assert len(merged.relations) == 1
    assert len(merged.claims) == 1
    assert merged.entities[0].name == "NutriPlus"
    assert merged.claims[0].source_doc_id == "doc-1"
