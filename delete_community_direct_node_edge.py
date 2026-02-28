import os
import json
import xml.etree.ElementTree as ET
from delete_utils import clean_node_id, get_logger

# Paths (remain unchanged)
GRAPHML_PATH = os.path.join("cache", "graph_chunk_entity_relation.graphml")
COMMUNITY_REPORTS_PATH = os.path.join("cache", "kv_store_community_reports.json")
DELETED_CACHE_PATH = "deleted_clusters_cache.json"

logger = get_logger()


def clean_id(raw: str) -> str:
    """
    Unescape HTML entities, strip outer quotes, and lowercase.
    E.g. '&quot;DUMBLEDORE&quot;' → 'dumbledore'
    """
    return clean_node_id(raw or "").strip().lower()


def load_graphml_clusters(graphml_path: str, raw_node_id: str) -> list[str]:
    """
    Parse the GraphML file, find the node whose cleaned id matches raw_node_id,
    extract its <data key="d3"> as JSON, and return the list of cluster IDs.
    """
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    tree = ET.parse(graphml_path)
    root = tree.getroot()
    target = raw_node_id.lower()

    for node in root.findall(".//g:node", ns):
        nid = clean_id(node.get("id", ""))
        if nid == target:
            data_elem = node.find('g:data[@key="d3"]', ns)
            if data_elem is None or not data_elem.text:
                raise ValueError(f"No <data key='d3'> for node {raw_node_id!r}")
            raw_text = data_elem.text.strip()
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, list) and all(isinstance(item, dict) and "cluster" in item for item in parsed):
                    return [str(item["cluster"]) for item in parsed]
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
                raise ValueError
            except Exception:
                sep = "," if "," in raw_text else "&lt;SEP&gt;"
                return [p.strip() for p in raw_text.split(sep) if p.strip()]

    raise ValueError(f"Node {raw_node_id!r} not found in {graphml_path}")


def load_community_reports(path: str) -> dict:
    """
    Load the community reports JSON, mapping cluster IDs to community data.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def gather_all_clusters(initial_ids: list[str], community_reports: dict) -> set[str]:
    """
    Starting from initial_ids, traverse 'sub_communities' recursively
    to collect every related cluster ID.
    """
    all_ids = set()
    def dfs(cid: str):
        if cid in all_ids:
            return
        all_ids.add(cid)
        for sub in community_reports.get(cid, {}).get("sub_communities", []):
            dfs(str(sub))
    for cid in initial_ids:
        dfs(str(cid))
    return all_ids


def update_and_persist(initial_cluster_ids: list[str],
                       raw_node_id: str,
                       community_reports: dict,
                       deleted_cache_path: str,
                       community_reports_path: str):
    """
    1) Collect all clusters (including nested sub_communities) for raw_node_id.
    2) Remove raw_node_id from their 'nodes' and 'edges' in community_reports.
    3) Write only the list of all affected cluster IDs to deleted_clusters_cache.json.
    4) Persist the updated community_reports back to disk.
    """
    target = raw_node_id.lower()

    # 1. gather all relevant cluster IDs
    all_cluster_ids = gather_all_clusters(initial_cluster_ids, community_reports)

    # 2. update community_reports in-memory
    for cid in all_cluster_ids:
        comm = community_reports.get(cid, {"nodes": [], "edges": []})
        orig_nodes = comm.get("nodes", [])
        orig_edges = comm.get("edges", [])

        # filter out raw_node_id
        comm["nodes"] = [n for n in orig_nodes if clean_id(n) != target]
        comm["edges"] = [
            e for e in orig_edges
            if clean_id(e[0]) != target and clean_id(e[1]) != target
        ]
        community_reports[cid] = comm

    # 3. write only the list of cluster IDs to deleted_clusters_cache.json
    with open(deleted_cache_path, "w", encoding="utf-8") as f:
        json.dump(list(all_cluster_ids), f, indent=2, ensure_ascii=False)

    # 4. persist updated community_reports back to disk
    with open(community_reports_path, "w", encoding="utf-8") as f:
        json.dump(community_reports, f, indent=2, ensure_ascii=False)


def main(raw_node_id: str):
    # find top-level clusters from GraphML
    initial = load_graphml_clusters(GRAPHML_PATH, raw_node_id)

    # load existing community reports
    reports = load_community_reports(COMMUNITY_REPORTS_PATH)

    # update and persist changes
    update_and_persist(
        initial_cluster_ids=initial,
        raw_node_id=raw_node_id,
        community_reports=reports,
        deleted_cache_path=DELETED_CACHE_PATH,
        community_reports_path=COMMUNITY_REPORTS_PATH
    )

    logger.info(f"Wrote {DELETED_CACHE_PATH} with clusters: {initial} for node {raw_node_id}")

if __name__ == "__main__":
    # Default behavior when run as script
    main("Dumbledore")