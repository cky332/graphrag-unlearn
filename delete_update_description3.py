#!/usr/bin/env python3
import os
import asyncio
import xml.etree.ElementTree as ET
import sys
from before_search import extract_entities
from delete_node_edge import remove_node_and_edges
from delete_utils import anonymize_text, get_logger

logger = get_logger()

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def update_graphml_descriptions(graphml_path: str, raw_node_id: str, raw_node_id2: str):
    """
    1. 加载 GraphML
    2. 找到 raw_node_id 的一跳邻居
    3. 对原节点和一跳节点的 key="d1" 描述，用 raw_node_id2 进行匿名化
    4. 对 hop=1 边（raw<->1hop）的 key="d5" 描述，使用 raw_node_id2 进行匿名化
    5. 写回文件，并输出一跳节点列表
    """
    ET.register_namespace("", "http://graphml.graphdrawing.org/xmlns")
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    tree = ET.parse(graphml_path)
    root = tree.getroot()

    target_norm = raw_node_id.strip().lower()
    raw_quoted = f'"{raw_node_id}"'

    one_hop = set()
    edges_1hop = []
    for edge in root.findall(".//g:edge", ns):
        src = edge.get("source")
        tgt = edge.get("target")
        if src.strip('"').lower() == target_norm and tgt.strip('"').lower() != target_norm:
            one_hop.add(tgt)
            edges_1hop.append(edge)
        elif tgt.strip('"').lower() == target_norm and src.strip('"').lower() != target_norm:
            one_hop.add(src)
            edges_1hop.append(edge)

    nodes_to_anonymize = {raw_quoted} | one_hop

    for node in root.findall(".//g:node", ns):
        if node.get("id") in nodes_to_anonymize:
            data = node.find('g:data[@key="d1"]', ns)
            if data is not None and data.text:
                data.text = anonymize_text(data.text, raw_node_id2)

    for edge in edges_1hop:
        data = edge.find('g:data[@key="d5"]', ns)
        if data is not None and data.text:
            data.text = anonymize_text(data.text, raw_node_id2)

    tree.write(graphml_path, encoding="utf-8", xml_declaration=True)
    print(f"Anonymized '{raw_node_id2}', its 1-hop neighbors and related edges in {graphml_path}")

    with open('one_hop_nodes.txt', 'w') as f:
        for node in one_hop:
            f.write(f"{node}\n")


async def process_entities(graphml_path: str, raw_node_id: str):
    entities = await extract_entities(raw_node_id, graphml_path)
    print(f"[Extracted Entities] 共 {len(entities)} 个：{entities}")

    for entity in entities:
        print(f"\n>>> Processing entity: {entity}")
        await update_graphml_descriptions(graphml_path, entity, raw_node_id)
        remove_node_and_edges(graphml_path, entity)
        print(f"[Done] Removed node & edges for '{entity}'.")


if __name__ == "__main__":
    cache_dir = "cache"
    graphml_path = os.path.join(cache_dir, 'graph_chunk_entity_relation.graphml')
    raw_node_id = 'Dumbledore'

    asyncio.run(process_entities(graphml_path, raw_node_id))
