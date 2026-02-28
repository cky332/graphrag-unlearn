import os
import asyncio
import xml.etree.ElementTree as ET
import sys
from before_search import extract_entities
from delete_node_edge import remove_node_and_edges
from delete_utils import anonymize_text, get_logger

# 在 Windows 上启用兼容的事件循环
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = get_logger()


async def update_graphml_descriptions(graphml_path: str, raw_node_id: str, raw_node_id2: str):
    """
    1. 加载 GraphML
    2. 找到 raw_node_id 的一跳、二跳和三跳邻居
    3. 对原节点、一跳、二跳和三跳节点的 key="d1" 描述，用 raw_node_id 进行匿名化
    4. 对 hop=1、hop=2、hop=3 边（分别是 raw<->1hop、1hop<->2hop、2hop<->3hop）的 key="d5" 描述，使用 raw_node_id 进行匿名化
    5. 写回文件
    """
    ET.register_namespace("", "http://graphml.graphdrawing.org/xmlns")
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}
    tree = ET.parse(graphml_path)
    root = tree.getroot()

    target_norm = raw_node_id.strip().lower()
    raw_quoted = f'"{raw_node_id}"'

    # 1. 收集一跳邻居及 raw<->1hop 边
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

    # 2. 收集二跳邻居及 1hop<->2hop 边
    two_hop = set()
    edges_2hop = []
    for edge in root.findall(".//g:edge", ns):
        src = edge.get("source")
        tgt = edge.get("target")
        if src in one_hop and tgt not in one_hop and tgt != raw_quoted:
            two_hop.add(tgt)
            edges_2hop.append(edge)
        elif tgt in one_hop and src not in one_hop and src != raw_quoted:
            two_hop.add(src)
            edges_2hop.append(edge)

    # 3. 收集三跳邻居及 2hop<->3hop 边
    three_hop = set()
    edges_3hop = []
    for edge in root.findall(".//g:edge", ns):
        src = edge.get("source")
        tgt = edge.get("target")
        if src in two_hop and tgt not in one_hop and tgt not in two_hop and tgt != raw_quoted:
            three_hop.add(tgt)
            edges_3hop.append(edge)
        elif tgt in two_hop and src not in one_hop and src not in two_hop and src != raw_quoted:
            three_hop.add(src)
            edges_3hop.append(edge)

    # 4. 构建所有要匿名化的节点集合（带引号形式）
    nodes_to_anonymize = {raw_quoted} | one_hop | two_hop | three_hop

    # 5. 匿名化节点描述（key="d1"），统一用 raw_node_id
    for node in root.findall(".//g:node", ns):
        if node.get("id") in nodes_to_anonymize:
            data = node.find('g:data[@key="d1"]', ns)
            if data is not None and data.text:
                data.text = anonymize_text(data.text, raw_node_id2)

    # 6. 匿名化所有相关边的描述（key="d5"），统一用 raw_node_id
    for edge in edges_1hop + edges_2hop + edges_3hop:
        data = edge.find('g:data[@key="d5"]', ns)
        if data is not None and data.text:
            data.text = anonymize_text(data.text, raw_node_id2)

    # 7. 写回文件
    tree.write(graphml_path, encoding="utf-8", xml_declaration=True)
    logger.info(f"Anonymized '{raw_node_id2}', its 1/2/3-hop neighbors and related edges in {graphml_path}")

    # 8. 将一跳、二跳和三跳节点分别写入不同文件
    with open('one_hop_nodes.txt', 'w', encoding='utf-8') as f:
        for node in one_hop:
            f.write(f"{node}\n")

    with open('two_hop_nodes.txt', 'w', encoding='utf-8') as f:
        for node in two_hop:
            f.write(f"{node}\n")

    with open('three_hop_nodes.txt', 'w', encoding='utf-8') as f:
        for node in three_hop:
            f.write(f"{node}\n")


async def process_entities(graphml_path: str, raw_node_id: str):
    # 从 before_search 提取实体
    entities = await extract_entities(raw_node_id, graphml_path)
    logger.info(f"[Extracted Entities] 共 {len(entities)} 个：{entities}")

    # 对每个提取的实体进行处理
    for entity in entities:
        logger.info(f">>> Processing entity: {entity}")
        # 调用 update_graphml_descriptions 处理每个实体
        await update_graphml_descriptions(graphml_path, entity, raw_node_id)

        remove_node_and_edges(graphml_path, entity)
        logger.info(f"[Done] Removed node & edges for '{entity}'.")


if __name__ == "__main__":
    cache_dir = "cache"
    graphml_path = os.path.join(cache_dir, 'graph_chunk_entity_relation.graphml')
    raw_node_id = 'Dumbledore'  # 传入不带引号的名称

    # 异步调用 process_entities 函数
    asyncio.run(process_entities(graphml_path, raw_node_id))
