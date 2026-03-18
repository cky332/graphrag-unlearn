import asyncio
import os
import sys
from nano_graphrag._storage.gdb_networkx import NetworkXStorage
import os
import sys
os.environ["OPENAI_API_KEY"]   = "sk-zk20d46549ec2e0e53b3d943323d2f87fd0681ca5c69cd6a"
os.environ["OPENAI_BASE_URL"]  = "https://api.zhizengzeng.com/v1/"
os.environ["HTTP_PROXY"]       = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"]      = "http://127.0.0.1:7890"

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    global_config = {
        "working_dir": "./cache2",
    }
    node_id   = '"DUMBLEDORE"'
    namespace = "chunk_entity_relation"

    storage = NetworkXStorage(namespace=namespace, global_config=global_config)

    edges = await storage.get_node_edges(node_id)
    connected_nodes = [tgt for _, tgt in (edges or [])]

    print(f"Nodes connected to {node_id}:")
    for tgt in connected_nodes:
        print(f"  - {tgt}")

    await storage.index_done_callback()

if __name__ == "__main__":
    asyncio.run(main())
