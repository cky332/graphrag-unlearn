import os
import json
import asyncio
import sys
import xml.etree.ElementTree as ET
from delete_utils import clean_node_id, anonymize_text, get_logger

# File paths for hop lists and GraphML
ONE_HOP_FILE = 'one_hop_nodes.txt'
TWO_HOP_FILE = 'two_hop_nodes.txt'
THREE_HOP_FILE = 'three_hop_nodes.txt'
GRAPHML_FILE = os.path.join('cache', 'graph_chunk_entity_relation.graphml')

logger = get_logger()


async def anonymize_all_chunks(
    kv_store_path: str,
    entity: str,
    raw_node_id_default: str
) -> dict[str, dict[str, str]]:
    """
    Anonymize text chunks related to an entity and its 1-3 hop neighbors.
    Steps:
    1. Read hop files (ignoring encoding errors) to build a set of entities.
    2. Parse GraphML to extract chunk IDs from <data key="d2"> for matching nodes.
    3. Load kv_store JSON (ignoring encoding errors) and anonymize each chunk's content.
    4. Overwrite kv_store and return mapping of original vs anonymized texts.
    """
    # 1. Build entity set
    entity_set = set()
    # Add main entity with quotes
    entity_set.add(f'"{entity}"')
    # Read hop lists (they already contain quoted names)
    for fname in (ONE_HOP_FILE, TWO_HOP_FILE, THREE_HOP_FILE):
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entity_set.add(line)

    # 2. Parse GraphML to collect chunk IDs
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

    # 3. Load and anonymize KV store
    if not os.path.isfile(kv_store_path):
        raise FileNotFoundError(f"KV store not found: {kv_store_path}")
    # Read JSON with ignore errors
    with open(kv_store_path, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            kv_store = json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in KV store: {kv_store_path}")

    results: dict[str, dict[str, str]] = {}
    for cid in chunk_ids:
        entry = kv_store.get(cid)
        if entry is None:
            continue
        # Handle string entries or dict entries with 'content'
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

    # 4. Save updated KV store
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

    try:
        results = await anonymize_all_chunks(
            kv_store_path, entity, raw_node_id_default
        )
    except (FileNotFoundError, ValueError, UnicodeDecodeError) as e:
        print("Error during anonymization:", e)
        return

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
