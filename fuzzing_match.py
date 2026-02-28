import os
import html
import xml.etree.ElementTree as ET
from delete_utils import load_api_config

load_api_config()
def find_matching_nodes(graphml_path: str, raw_node_id: str):
    """
    从 GraphML 文件中查找所有节点 ID 中包含 raw_node_id（忽略大小写）的 <node> 元素。

    Args:
        graphml_path: GraphML 文件路径。
        raw_node_id: 要匹配的原始节点标识符（不区分大小写）。

    Returns:
        List of tuples: (cleaned_id, node_xml_string)
    """
    # 解析 XML
    tree = ET.parse(graphml_path)
    root = tree.getroot()
    # GraphML 默认命名空间
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}

    matches = []
    # 递归地查找所有 <node> 元素（可能在 <graph> 之下）
    for node in root.findall('.//g:node', ns):
        id_attr = node.get('id')
        if not id_attr:
            continue

        # xml.etree 已将 &quot; 解析为实际的双引号，这里做一次 html.unescape 以防万一
        id_unescaped = html.unescape(id_attr)

        # 去除外层的双引号（如果存在）
        if id_unescaped.startswith('"') and id_unescaped.endswith('"'):
            id_clean = id_unescaped[1:-1]
        else:
            id_clean = id_unescaped

        # 忽略大小写的模糊匹配
        if raw_node_id.lower() in id_clean.lower():
            # 以字符串形式输出整个 <node> 元素
            node_xml = ET.tostring(node, encoding='unicode')
            matches.append((id_clean, node_xml))

    return matches

def main():
    # —— 直接指定 GraphML 路径和要匹配的 raw_node_id —— 
    graphml_file = os.path.join('cache', 'graph_chunk_entity_relation.graphml')
    raw_node_id = "Dumbledore"

    if not os.path.isfile(graphml_file):
        print(f"文件不存在: {graphml_file}")
        return

    matches = find_matching_nodes(graphml_file, raw_node_id)
    if not matches:
        print(f"未在 '{graphml_file}' 中找到包含 '{raw_node_id}' 的节点。")
        return

    print(f"在 '{graphml_file}' 中共找到 {len(matches)} 个匹配节点（raw_node_id='{raw_node_id}'）：\n")
    for idx, (node_id, node_xml) in enumerate(matches, 1):
        print(f"--- 匹配 #{idx} ---")
        print(f"Node ID: {node_id}")
        print(node_xml)
        print()

if __name__ == "__main__":
    main()