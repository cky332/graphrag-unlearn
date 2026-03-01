
import os
import html
import json
import asyncio
import re
import sys
from delete_vdb_entities import delete_vdb_entities
from before_search import extract_entities
from delete_update_description import update_graphml_descriptions
from delete_node_edge import remove_node_and_edges
from delete_community import delete_community_pipeline
from delete_text_chunk import anonymize_all_chunks
import xml.etree.ElementTree as ET

def clean_node_id(raw: str) -> str:
    """Restore HTML entities and strip outer quotes."""
    unesc = html.unescape(raw)
    return unesc[1:-1] if unesc.startswith('"') and unesc.endswith('"') else unesc


def anonymize_text(chunk_text: str, raw_node_id: str) -> str:
    """
    Replace all occurrences of raw_node_id (case-insensitive),
    including possessive forms, with [mask].
    Ensure HTML entities are unescaped before masking.
    """
    text = html.unescape(chunk_text)
    pattern = re.compile(rf"\b{re.escape(raw_node_id)}(?:['’]s)?\b", re.IGNORECASE)
    return pattern.sub('[mask]', text)

async def main():
    raw_node_id_default = 'Dumbledore'
    cache_dir = 'cache'

    vdb_path = os.path.join(cache_dir, 'vdb_entities.json')
    graphml_path = os.path.join(cache_dir, 'graph_chunk_entity_relation.graphml')
    kv_store_path = os.path.join(cache_dir, 'kv_store_text_chunks.json')

    entities = await extract_entities(raw_node_id_default, graphml_path)
    print(f"[Extracted Entities] 共 {len(entities)} 个：{entities}")

    for entity in entities:
        print(f"\n>>> Processing entity: {entity}")

        remove_node_and_edges(graphml_path, entity)
        print(f"[Done] Removed node & edges for '{entity}'.")


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())