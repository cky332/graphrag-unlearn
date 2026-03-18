from nano_graphrag import GraphRAG, QueryParam
import os
os.environ["OPENAI_API_KEY"]   = "sk-zk20d46549ec2e0e53b3d943323d2f87fd0681ca5c69cd6a"
os.environ["OPENAI_BASE_URL"]  = "https://api.zhizengzeng.com/v1/"
os.environ["HTTP_PROXY"]       = "http://127.0.0.1:7890"
os.environ["HTTPS_PROXY"]      = "http://127.0.0.1:7890"
graph = GraphRAG(working_dir="./cache")

print(graph.query(
    "What are the top themes in this story?",
    param=QueryParam(mode="local")
))