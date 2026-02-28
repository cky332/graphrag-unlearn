#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import copy
import xml.etree.ElementTree as ET
from delete_utils import get_logger

logger = get_logger()

# ———————— 配置区 ————————
DELETED_JSON     = "deleted_clusters_cache.json"
REPORTS_JSON     = "cache/kv_store_community_reports.json"
GRAPHML_IN       = "cache/graph_chunk_entity_relation.graphml"
GRAPHML_OUT      = "graph_chunk_entity_relation2.graphml"

NS = {
    'g': "http://graphml.graphdrawing.org/xmlns",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance"
}
# 注册 namespace，保证写出时不带 ns0 前缀
ET.register_namespace('', NS['g'])
ET.register_namespace('xsi', NS['xsi'])
# ——————————————————————

def load_deleted_level0(path):
    logger.info(f"[DEBUG] Loading deleted clusters from: {path}")
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list) and all(isinstance(x, str) for x in data):
        logger.info(f"[DEBUG] Found simple list of cluster IDs: {data}")
        return set(data)
    level0_ids = []
    if isinstance(data, list):
        logger.info("[DEBUG] Found list of dicts, scanning for level==0 entries")
        for item in data:
            if isinstance(item, dict) and item.get('level') == 0 and 'cluster' in item:
                level0_ids.append(str(item['cluster']))
        logger.info(f"[DEBUG] Extracted level-0 clusters: {level0_ids}")
        return set(level0_ids)
    if isinstance(data, dict):
        logger.info("[DEBUG] Found dict mapping cluster_id -> info, scanning for level==0")
        for cid, info in data.items():
            if isinstance(info, dict) and info.get('level') == 0:
                level0_ids.append(str(cid))
        logger.info(f"[DEBUG] Extracted level-0 clusters: {level0_ids}")
        return set(level0_ids)
    logger.info("[DEBUG] Unrecognized format for deleted_clusters, returning empty set")
    return set()

def load_reports_nodes_edges(path, cluster_ids):
    logger.info(f"[DEBUG] Loading community report from: {path}")
    with open(path, encoding='utf-8') as f:
        reports = json.load(f)
    nodes = set()
    edges = set()
    for cid in cluster_ids:
        rep = reports.get(str(cid))
        if not rep:
            logger.info(f"[WARN] Cluster ID {cid} not found in reports")
            continue
        logger.info(f"[DEBUG] Cluster {cid}: {len(rep.get('nodes', []))} nodes, {len(rep.get('edges', []))} edges")
        nodes.update(rep.get('nodes', []))
        for e in rep.get('edges', []):
            edges.add((e[0], e[1]))
    logger.info(f"[DEBUG] Total nodes collected: {len(nodes)}; edges collected: {len(edges)}")
    return nodes, edges

def extract_subgraph(graphml_in, wanted_nodes, wanted_edges):
    logger.info(f"[DEBUG] Parsing GraphML input: {graphml_in}")
    tree = ET.parse(graphml_in)
    root = tree.getroot()

    # 复制 <key> 定义
    key_elems = [copy.deepcopy(e) for e in root.findall(f'{{{NS["g"]}}}key')]
    logger.info(f"[DEBUG] Found {len(key_elems)} <key> elements")

    # 创建新的 root 和 graph
    new_root = ET.Element(root.tag, root.attrib)
    for k in key_elems:
        new_root.append(k)

    orig_graph = root.find(f'{{{NS["g"]}}}graph')
    new_graph = ET.SubElement(new_root, orig_graph.tag, orig_graph.attrib)

    # 添加节点：注意从 <graph> 元素中查找
    added_nodes = 0
    for node in orig_graph.findall(f'{{{NS["g"]}}}node'):
        nid = node.get('id')
        if nid in wanted_nodes:
            new_graph.append(copy.deepcopy(node))
            logger.info(f"[DEBUG] Added node: {repr(nid)}")
            added_nodes += 1
        else:
            logger.info(f"[TRACE] Skipped node: {repr(nid)}")
    logger.info(f"[DEBUG] Total nodes added: {added_nodes}")

    # 添加边：同样从 <graph> 元素中查找
    added_edges = 0
    for edge in orig_graph.findall(f'{{{NS["g"]}}}edge'):
        src = edge.get('source')
        tgt = edge.get('target')
        if (src, tgt) in wanted_edges:
            new_graph.append(copy.deepcopy(edge))
            logger.info(f"[DEBUG] Added edge: ({repr(src)} -> {repr(tgt)})")
            added_edges += 1
        else:
            logger.info(f"[TRACE] Skipped edge: ({repr(src)} -> {repr(tgt)})")
    logger.info(f"[DEBUG] Total edges added: {added_edges}")

    return ET.ElementTree(new_root)

def main():
    # 1. 找到 level=0 的社区
    level0 = load_deleted_level0(DELETED_JSON)
    logger.info(f"[DEBUG] Level-0 clusters to process: {level0}")
    if not level0:
        logger.info("[ERROR] 未找到任何 level=0 的社区，退出。")
        return

    # 2. 从报告中收集节点和边
    nodes, edges = load_reports_nodes_edges(REPORTS_JSON, level0)
    if not nodes and not edges:
        logger.info("[ERROR] 对应社区在报告中没有找到节点或边，退出。")
        return

    # 3. 提取子图并写入新文件
    logger.info("[INFO] 开始提取子图...")
    subgraph_tree = extract_subgraph(GRAPHML_IN, nodes, edges)
    subgraph_tree.write(
        GRAPHML_OUT,
        encoding='utf-8',
        xml_declaration=True
    )
    logger.info(f"[INFO] 成功生成子图文件: {GRAPHML_OUT}")

if __name__ == "__main__":
    main()
