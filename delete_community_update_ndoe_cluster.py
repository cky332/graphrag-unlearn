import os
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from delete_utils import get_logger

logger = get_logger()

WORKDIR      = "."
CACHE_DIR    = "cache"
CACHE_FILE   = os.path.join(CACHE_DIR, "graph_chunk_entity_relation.graphml")
FILE2        = os.path.join(WORKDIR, "graph_chunk_entity_relation2.graphml")
FILE3        = os.path.join(WORKDIR, "graph_chunk_entity_relation3.graphml")
KV_FILE      = os.path.join(WORKDIR, "kv_store_community_reports3.json")
CLUSTERS_KEY = "d3"

GRAPHML_NS = "http://graphml.graphdrawing.org/xmlns"
XSI_NS     = "http://www.w3.org/2001/XMLSchema-instance"
ET.register_namespace("", GRAPHML_NS)
ET.register_namespace("xsi", XSI_NS)


def main():
    with open(KV_FILE, encoding="utf-8") as f:
        reports = json.load(f)

    node_to_comms = defaultdict(list)
    for comm_id, comm in reports.items():
        for node_id in comm.get("nodes", []):
            node_to_comms[node_id].append(comm_id)

    tree2 = ET.parse(FILE2)
    ids2 = {n.get("id") for n in tree2.findall(f".//{{{GRAPHML_NS}}}node")}

    logger.info(f"Updating {CACHE_FILE} for {len(ids2)} nodes from {FILE2}...")
    tree_cache = ET.parse(CACHE_FILE)
    root_cache = tree_cache.getroot()
    updated_cache = 0

    for node in root_cache.findall(f".//{{{GRAPHML_NS}}}node"):
        nid = node.get("id")
        if nid not in ids2:
            continue
        updated_cache += 1
        logger.info(f"[CACHE] Resetting node {nid}")

        data_elem = next(
            (d for d in node.findall(f"{{{GRAPHML_NS}}}data") if d.get("key") == CLUSTERS_KEY),
            None
        )
        if data_elem is None:
            data_elem = ET.SubElement(node, f"{{{GRAPHML_NS}}}data")
            data_elem.set("key", CLUSTERS_KEY)
        data_elem.text = ""

        comm_ids = node_to_comms.get(nid, [])
        objs = [{"level": idx, "cluster": int(cid)} for idx, cid in enumerate(comm_ids)]
        logger.info(f"  -> setting d3 to: {objs}")
        data_elem.text = json.dumps(objs)

    tree_cache.write(CACHE_FILE, encoding="utf-8", xml_declaration=True)
    logger.info(f"Done. {updated_cache} nodes reset in {CACHE_FILE}")

    logger.info(f"Updating {FILE3} for nodes in FILE3 \\ FILE2...")
    tree3 = ET.parse(FILE3)
    root3 = tree3.getroot()
    ids3 = {n.get("id") for n in root3.findall(f".//{{{GRAPHML_NS}}}node")}
    new_ids = ids3 - ids2
    updated3 = 0

    for node in root3.findall(f".//{{{GRAPHML_NS}}}node"):
        nid = node.get("id")
        if nid not in new_ids:
            continue
        updated3 += 1
        logger.info(f"[FILE3] Appending for new node {nid}")

        data_elem = next(
            (d for d in node.findall(f"{{{GRAPHML_NS}}}data") if d.get("key") == CLUSTERS_KEY),
            None
        )
        if data_elem is None:
            data_elem = ET.SubElement(node, f"{{{GRAPHML_NS}}}data")
            data_elem.set("key", CLUSTERS_KEY)
            existing = []
        else:
            try:
                existing = json.loads(data_elem.text or "[]")
            except json.JSONDecodeError:
                existing = []
            logger.info(f"  -> existing clusters: {existing}")

        comm_ids = node_to_comms.get(nid, [])
        objs = [{"level": idx, "cluster": int(cid)} for idx, cid in enumerate(comm_ids)]
        present = {o["cluster"] for o in existing if "cluster" in o}
        to_add = [o for o in objs if o["cluster"] not in present]
        combined = existing + to_add
        logger.info(f"  -> adding {to_add}, combined: {combined}")

        data_elem.text = json.dumps(combined)

    tree3.write(FILE3, encoding="utf-8", xml_declaration=True)
    logger.info(f"Done. {updated3} nodes updated in {FILE3}")


if __name__ == "__main__":
    main()
