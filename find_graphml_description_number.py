#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import re

def count_dumbledore_descriptions(graphml_path: str):
    """
    Parse the GraphML file at graphml_path, count how many node descriptions (data key="d1")
    and edge descriptions (data key="d5") contain the substring "Dumbledore" (case-insensitive).
    """
    tree = ET.parse(graphml_path)
    root = tree.getroot()

    m = re.match(r'\{(.+)\}', root.tag)
    if m:
        ns_uri = m.group(1)
        ns = {'g': ns_uri}
        node_xpath = './/g:node'
        edge_xpath = './/g:edge'
        data_tag = 'g:data'
    else:
        ns = {}
        node_xpath = './/node'
        edge_xpath = './/edge'
        data_tag = 'data'

    pattern = re.compile(r'Dumbledore', re.IGNORECASE)

    count_nodes = 0
    count_edges = 0

    for node in root.findall(node_xpath, ns):
        for d in node.findall(data_tag, ns):
            if d.get('key') == 'd1' and d.text and pattern.search(d.text):
                count_nodes += 1
                break

    for edge in root.findall(edge_xpath, ns):
        for d in edge.findall(data_tag, ns):
            if d.get('key') == 'd5' and d.text and pattern.search(d.text):
                count_edges += 1
                break

    total = count_nodes + count_edges
    print(f"Nodes containing 'Dumbledore': {count_nodes}")
    print(f"Edges containing 'Dumbledore': {count_edges}")
    print(f"Total descriptions containing 'Dumbledore': {total}")


if __name__ == "__main__":
    graphml_file = r"cache\graph_chunk_entity_relation.graphml"
    count_dumbledore_descriptions(graphml_file)
