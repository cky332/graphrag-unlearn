import os
import html
import json
import asyncio
import re
import sys
import xml.etree.ElementTree as ET

ONE_HOP_FILE = 'one_hop_nodes.txt'
TWO_HOP_FILE = 'two_hop_nodes.txt'
THREE_HOP_FILE = 'three_hop_nodes.txt'
GRAPHML_FILE = os.path.join('cache', 'graph_chunk_entity_relation.graphml')


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


async def anonymize_all_chunks(
    kv_store_path: str,
    entity: str,
    raw_node_id_default: str
) -> dict[str, dict[str, str]]:
    """
    Anonymize text chunks related to an entity and its 1-3 hop neighbors.
    Steps:
    1. Read hop files to build a set of entities (including the main entity).
    2. Parse GraphML to extract chunk IDs from <data key="d2"> for matching nodes.
    3. Load kv_store JSON and anonymize each chunk's content for raw_node_id_default.
    4. Overwrite kv_store and return mapping of original vs anonymized texts.
    """
    entity_set = set()
    entity_set.add(f'"{entity}"')
    for fname in (ONE_HOP_FILE, TWO_HOP_FILE, THREE_HOP_FILE):
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entity_set.add(line)

    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    tree = ET.parse(GRAPHML_FILE)
    root = tree.getroot()
    chunk_ids: set[str] = set()
    for node in root.findall('.//g:node', ns):
        node_id = node.get('id')
        if node_id in entity_set:
            data_elem = node.find('g:data[@key="d2"]', ns)
            if data_elem is not None and data_elem.text:
                parts = data_elem.text.split('<SEP>')
                chunk_ids.update(parts)

    if not os.path.isfile(kv_store_path):
        raise FileNotFoundError(f"KV store not found: {kv_store_path}")
    with open(kv_store_path, 'r', encoding='utf-8') as f:
        kv_store = json.load(f)

    results: dict[str, dict[str, str]] = {}
    for cid in chunk_ids:
        entry = kv_store.get(cid)
        if entry is None:
            continue
        if isinstance(entry, str):
            original = entry
            anonymized = anonymize_text(original, raw_node_id_default)
            kv_store[cid] = {'content': anonymized, 'tokens': len(anonymized.split())}
        elif isinstance(entry, dict) and 'content' in entry:
            original = entry['content']
            anonymized = anonymize_text(original, raw_node_id_default)
            entry['content'] = anonymized
            entry['tokens'] = len(anonymized.split())
        else:
            continue
        results[cid] = {'original': original, 'anonymized': anonymized}

    with open(kv_store_path, 'w', encoding='utf-8') as f:
        json.dump(kv_store, f, ensure_ascii=False, indent=2)

    return results


async def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python delete_text_chunk.py <kv_store_path> <entity> <raw_node_id_default>"
        )
        return
    kv_store_path, entity, raw_node_id_default = sys.argv[1], sys.argv[2], sys.argv[3]

    results = await anonymize_all_chunks(
        kv_store_path, entity, raw_node_id_default
    )
    if not results:
        print(f"No chunks found in '{kv_store_path}' to anonymize for entity {entity}.")
        return
    for cid, data in results.items():
        print(f"\n=== Chunk ID: {cid} ===")
        print('➜ Original:\n', data['original'])
        print('➜ Anonymized:\n', data['anonymized'])


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
