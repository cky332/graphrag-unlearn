#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import xml.etree.ElementTree as ET
from delete_utils import get_logger

logger = get_logger()

GRAPHML2_IN     = "graph_chunk_entity_relation2.graphml"
GRAPHML_ORIG    = "cache/graph_chunk_entity_relation.graphml"
GRAPHML3_OUT    = "graph_chunk_entity_relation3.graphml"

NS = {
    'g':   "http://graphml.graphdrawing.org/xmlns",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance"
}
ET.register_namespace('', NS['g'])
ET.register_namespace('xsi', NS['xsi'])

def main():
    tree2 = ET.parse(GRAPHML2_IN)
    root2 = tree2.getroot()
    graph2 = root2.find(f'{{{NS["g"]}}}graph')

    existing_nodes = {
        node.get('id')
        for node in graph2.findall(f'{{{NS["g"]}}}node')
    }

    referenced = set()
    for edge in graph2.findall(f'{{{NS["g"]}}}edge'):
        referenced.add(edge.get('source'))
        referenced.add(edge.get('target'))

    missing = referenced - existing_nodes
    logger.info(f"[DEBUG] Referenced nodes: {len(referenced)}, existing nodes: {len(existing_nodes)}, missing: {missing}")

    if not missing:
        logger.info("[INFO] 无缺失节点，直接复制为第三版文件。")
        tree2.write(GRAPHML3_OUT, encoding='utf-8', xml_declaration=True)
        return

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

    tree2.write(GRAPHML3_OUT, encoding='utf-8', xml_declaration=True)
    logger.info(f"[INFO] 成功生成完整文件: {GRAPHML3_OUT}")

if __name__ == "__main__":
    main()
