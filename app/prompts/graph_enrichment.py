from __future__ import annotations

import json

from app.domain.models import Chunk


GRAPH_ENRICHMENT_PROMPT_VERSION = "graph-enrichment-v1"

GRAPH_ENRICHMENT_SYSTEM_PROMPT = """
You extract graph entities and typed relations from technical documentation chunks.
Return JSON only with this schema:
{
  "entities": {
    "products": [string],
    "interfaces": [string],
    "os_tags": [string],
    "language_tags": [string],
    "components": [string],
    "api_symbols": [string],
    "pkcs11_objects": [string],
    "pkcs11_mechanisms": [string],
    "error_codes": [string]
  },
  "relations": [
    {
      "src_type": string,
      "src_value": string,
      "predicate": string,
      "tgt_type": string,
      "tgt_value": string,
      "confidence": number,
      "evidence": string
    }
  ]
}

Allowed predicates:
- supports_interface
- available_on_os
- uses_component
- belongs_to_interface
- returns_error_code
- uses_pkcs11_object
- uses_mechanism
- compatible_with

Rules:
- Extract only facts supported by the chunk.
- Prefer canonical values when obvious.
- Do not invent entities or relations.
- Confidence must be between 0 and 1.
""".strip()


def build_graph_enrichment_prompt(chunk: Chunk) -> str:
    payload = {
        "title": chunk.title,
        "heading_path": chunk.heading_path,
        "chunk_type": chunk.chunk_type,
        "text": chunk.text,
        "rule_entities": chunk.metadata.get("graph_entities_rule", {}),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
