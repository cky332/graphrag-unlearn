#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import xml.etree.ElementTree as ET
from delete_utils import get_logger

logger = get_logger()

# ———————— 配置区 ————————
GRAPHML2_IN     = "graph_chunk_entity_relation2.graphml"
GRAPHML_ORIG    = "cache/graph_chunk_entity_relation.graphml"
GRAPHML3_OUT    = "graph_chunk_entity_relation3.graphml"

NS = {
    'g':   "http://graphml.graphdrawing.org/xmlns",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance"
}
# 注册 namespace，保证写出时不带 ns0 前缀
ET.register_namespace('', NS['g'])
ET.register_namespace('xsi', NS['xsi'])
# ——————————————————————

def main():
    # 1. 解析第二步生成的 subgraph（可能缺少一些被边引用的节点）
    tree2 = ET.parse(GRAPHML2_IN)
    root2 = tree2.getroot()
    graph2 = root2.find(f'{{{NS["g"]}}}graph')

    # 收集已存在的节点 ID
    existing_nodes = {
        node.get('id')
        for node in graph2.findall(f'{{{NS["g"]}}}node')
    }

    # 收集所有边的 source/target 引用
    referenced = set()
    for edge in graph2.findall(f'{{{NS["g"]}}}edge'):
        referenced.add(edge.get('source'))
        referenced.add(edge.get('target'))

    # 找出缺失的节点 ID
    missing = referenced - existing_nodes
    logger.info(f"[DEBUG] Referenced nodes: {len(referenced)}, existing nodes: {len(existing_nodes)}, missing: {missing}")

    if not missing:
        logger.info("[INFO] 无缺失节点，直接复制为第三版文件。")
        tree2.write(GRAPHML3_OUT, encoding='utf-8', xml_declaration=True)
        return

    # 2. 从原始大图中提取这些缺失的节点
    tree1 = ET.parse(GRAPHML_ORIG)
    root1 = tree1.getroot()
    graph1 = root1.find(f'{{{NS["g"]}}}graph')

    added = 0
    for node in graph1.findall(f'{{{NS["g"]}}}node'):
        nid = node.get('id')
        if nid in missing:
            graph2.append(copy.deepcopy(node))
            logger.info(f"[DEBUG] Added missing node: {repr(nid)}")
            added += 1

    logger.info(f"[INFO] 共添加 {added} 个缺失节点到第二版子图中。")

    # 3. 输出合并后的第三版 GraphML
    tree2.write(GRAPHML3_OUT, encoding='utf-8', xml_declaration=True)
    logger.info(f"[INFO] 成功生成完整文件: {GRAPHML3_OUT}")

if __name__ == "__main__":
    main()
