#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import networkx as nx
import os
from delete_utils import get_logger, load_json as _load_json

logger = get_logger()

# ———————— 配置区 ————————
DELETED_CACHE = 'deleted_clusters_cache.json'
REPORTS1      = os.path.join('cache',  'kv_store_community_reports.json')
REPORTS2      = os.path.join('cache2', 'kv_store_community_reports.json')
FLAG_FILE     = 'cluster_change_flags.json'

CLUSTERING_DELTA    = 0.1
ASSORTATIVITY_DELTA = 0.1
DENSITY_DELTA       = 0.05
# ——————————————————————

def load_json(path: str):
    logger.info(f"Loading JSON from {path!r}")
    data = _load_json(path)
    size = len(data) if hasattr(data, '__len__') else 'N/A'
    logger.info(f"Loaded {type(data).__name__} with {size} entries")
    return data

def get_level0_clusters(deleted_data, community_reports):
    logger.info("[INFO] Extracting level-0 clusters from deleted data")
    level0 = []
    if isinstance(deleted_data, dict):
        for k, v in deleted_data.items():
            if isinstance(v, dict) and v.get('level') == 0:
                logger.info(f"  - Found dict cluster {k} level=0")
                level0.append({'cluster': k})
            elif isinstance(v, (int, float)) and v == 0:
                logger.info(f"  - Found numeric cluster {k} == 0")
                level0.append({'cluster': k})
    elif isinstance(deleted_data, list):
        for e in deleted_data:
            if isinstance(e, dict) and e.get('level') == 0:
                cid = e.get('cluster')
                logger.info(f"  - Found list-dict cluster {cid} level=0")
                level0.append({'cluster': cid})
            else:
                cid = str(e)
                info = community_reports.get(cid, {})
                lvl = info.get('level')
                logger.info(f"  - Checking list-element cluster {cid}, report level={lvl}")
                if lvl == 0:
                    level0.append({'cluster': cid})
    logger.info(f"[INFO] Total level-0 clusters: {len(level0)} -> {[c['cluster'] for c in level0]}")
    return level0

def build_graph(nodes, edges):
    G = nx.Graph()
    G.add_nodes_from(nodes)
    G.add_edges_from((src, tgt) for src, tgt in edges)
    return G

def evaluate_clusters(deleted, reports1, reports2):
    """
    返回 True 如果至少有一个 level=0 社区的任何指标超过阈值，否则 False。
    """
    logger.info("[INFO] Evaluating clusters against thresholds:")
    logger.info(f"  CLUSTERING_DELTA    = {CLUSTERING_DELTA}")
    logger.info(f"  ASSORTATIVITY_DELTA = {ASSORTATIVITY_DELTA}")
    logger.info(f"  DENSITY_DELTA       = {DENSITY_DELTA}")
    level0 = get_level0_clusters(deleted, reports1)
    for entry in level0:
        cid = str(entry['cluster'])
        logger.info(f"\n[INFO] Processing community {cid}")
        comm1 = reports1.get(cid)
        comm2 = reports2.get(cid)
        if not comm1 or not comm2:
            logger.info(f"[WARN] Missing nodes/edges for community {cid}, skipping")
            continue

        nodes1, edges1 = comm1.get('nodes', []), comm1.get('edges', [])
        nodes2, edges2 = comm2.get('nodes', []), comm2.get('edges', [])
        logger.info(f"  nodes1={len(nodes1)}, edges1={len(edges1)}")
        logger.info(f"  nodes2={len(nodes2)}, edges2={len(edges2)}")

        G1 = build_graph(nodes1, edges1)
        G2 = build_graph(nodes2, edges2)

        c1, c2 = nx.average_clustering(G1), nx.average_clustering(G2)
        a1, a2 = nx.degree_assortativity_coefficient(G1), nx.degree_assortativity_coefficient(G2)
        d1, d2 = nx.density(G1), nx.density(G2)

        logger.info(f"  Avg clustering:  {c1:.4f} → {c2:.4f} (Δ={abs(c1-c2):.4f})")
        logger.info(f"  Assortativity:   {a1:.4f} → {a2:.4f} (Δ={abs(a1-a2):.4f})")
        logger.info(f"  Density:         {d1:.4f} → {d2:.4f} (Δ={abs(d1-d2):.4f})")

        if (
            abs(c1 - c2) > CLUSTERING_DELTA or
            abs(a1 - a2) > ASSORTATIVITY_DELTA or
            abs(d1 - d2) > DENSITY_DELTA
        ):
            logger.info(f"[RESULT] Community {cid}: CHANGE detected")
            return True
        else:
            logger.info(f"[RESULT] Community {cid}: No significant change")

    logger.info("\n[INFO] No level-0 community exceeded thresholds")
    return False

def main():
    logger.info("[START] cluster change evaluation script")
    deleted  = load_json(DELETED_CACHE)
    reports1 = load_json(REPORTS1)
    reports2 = load_json(REPORTS2)

    changed = evaluate_clusters(deleted, reports1, reports2)
    logger.info(f"\n[FINAL] Overall changed = {changed}")

    # 写入文件：仅 "true" 或 "false"
    with open(FLAG_FILE, 'w', encoding='utf-8') as f:
        f.write("true" if changed else "false")
    logger.info(f"[INFO] Wrote flag to {FLAG_FILE}: {'true' if changed else 'false'}")

    # 最终控制台输出
    logger.info("true" if changed else "false")

if __name__ == '__main__':
    main()
