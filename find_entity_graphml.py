import xml.etree.ElementTree as ET
import os

def strip_ns(tag: str) -> str:
    """Remove namespace from XML tag."""
    return tag[tag.find("}")+1:] if "}" in tag else tag

def extract_dumbledore_elements(input_path: str, output_path: str):
    tree = ET.parse(input_path)
    root = tree.getroot()

    ns_uri = root.tag[root.tag.find("{")+1:root.tag.find("}")]
    ns_map = {'g': ns_uri}

    extracted = []

    for node in root.findall('.//g:node', ns_map):
        raw_id = node.get('id', '').strip('"').strip()
        if raw_id.lower() == 'dumbledore':
            extracted.append(node)

    for edge in root.findall('.//g:edge', ns_map):
        src = edge.get('source', '').strip('"').strip().lower()
        tgt = edge.get('target', '').strip('"').strip().lower()
        if src == 'dumbledore' or tgt == 'dumbledore':
            extracted.append(edge)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<graphml_extract>\n')

        for elem in extracted:
            tag = strip_ns(elem.tag)
            attrs = " ".join(f'{strip_ns(k)}="{v}"' for k, v in elem.items())
            f.write(f'  <{tag} {attrs}>\n')

            for child in elem:
                child_tag = strip_ns(child.tag)
                key = child.get('key')
                text = child.text or ""
                f.write(f'    <{child_tag} key="{key}">{text}</{child_tag}>\n')

            f.write(f'  </{tag}>\n')

        f.write('</graphml_extract>\n')

if __name__ == '__main__':
    input_file = os.path.join('cache2', 'graph_chunk_entity_relation.graphml')
    output_file = 'graphml_extract.graphml'
    extract_dumbledore_elements(input_file, output_file)
    print(f"Extraction complete. Output saved to {output_file}")
