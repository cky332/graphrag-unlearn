import os
import json
import sys
import xml.etree.ElementTree as ET
from delete_utils import anonymize_text, get_logger

logger = get_logger()

# Paths and constants
CACHE_DIR = ‘cache’
GRAPHML_FILE = os.path.join(CACHE_DIR, ‘graph_chunk_entity_relation.graphml’)
HOP_FILES = [‘two_hop_nodes.txt’, ‘three_hop_nodes.txt’]
COMMUNITY_REPORTS_FILE = os.path.join(CACHE_DIR, ‘kv_store_community_reports.json’)


def update_reports_for_entity(raw_node_id_default: str) -> None:
    """
    For each node in two_hop and three_hop lists, find its clusters in GRAPHML,
    then for each cluster id, load the corresponding community report and
    anonymize any occurrences of raw_node_id_default in both report_string and report_json.
    Save the updated community reports back to JSON.
    """
    # 1. Load hop nodes
    entities = set()
    for fname in HOP_FILES:
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    val = line.strip()
                    if val:
                        entities.add(val)

    if not entities:
        logger.info("No hop nodes found.")
        return

    # 2. Parse GraphML and collect cluster ids
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    tree = ET.parse(GRAPHML_FILE)
    root = tree.getroot()
    cluster_ids = set()
    for node in root.findall('.//g:node', ns):
        node_id = node.get('id')
        if node_id in entities:
            data_elem = node.find('g:data[@key="d3"]', ns)
            if data_elem is not None and data_elem.text:
                try:
                    clusters = json.loads(data_elem.text)
                    for c in clusters:
                        # collect numeric cluster id as string key
                        cluster_ids.add(str(c.get('cluster')))
                except json.JSONDecodeError:
                    continue

    if not cluster_ids:
        logger.info("No cluster IDs found for given entities.")
        return

    # 3. Load community reports
    if not os.path.isfile(COMMUNITY_REPORTS_FILE):
        raise FileNotFoundError(f"Community reports file not found: {COMMUNITY_REPORTS_FILE}")
    with open(COMMUNITY_REPORTS_FILE, 'r', encoding='utf-8') as f:
        reports = json.load(f)

    updated = False
    raw_lower = raw_node_id_default.lower()

    # 4. Process each cluster report
    for cid in cluster_ids:
        community = reports.get(cid)
        if not isinstance(community, dict):
            continue

        # Combine existing content
        report_string = community.get('report_string', '')
        report_json = community.get('report_json', {})
        combined = (report_string or '').lower() + json.dumps(report_json or {}).lower()

        if raw_lower in combined:
            # Anonymize report_string
            new_string = anonymize_text(report_string, raw_node_id_default)
            community['report_string'] = new_string

            # Recursively anonymize all string fields in report_json
            def recurse(obj):
                if isinstance(obj, str):
                    return anonymize_text(obj, raw_node_id_default)
                elif isinstance(obj, dict):
                    return {k: recurse(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [recurse(item) for item in obj]
                else:
                    return obj

            community['report_json'] = recurse(report_json)
            reports[cid] = community
            logger.info(f"Anonymized community report for cluster {cid}.")
            updated = True

    # 5. Save changes if any
    if updated:
        with open(COMMUNITY_REPORTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        logger.info("Community reports updated and saved.")
    else:
        logger.info("No community reports required anonymization.")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python delete_community_update_reports_last.py <raw_node_id_default>")
    else:
        update_reports_for_entity(sys.argv[1])
