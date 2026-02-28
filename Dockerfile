FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（hnswlib 编译需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# 先安装 Python 依赖（利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY nano_graphrag/ ./nano_graphrag/
COPY delete_utils.py delete_node_edge.py delete_text_chunk.py delete_vdb_entities.py ./
COPY delete_update_description.py delete_update_description2.py delete_update_description3.py ./
COPY delete_community.py delete_community_direct_node_edge.py delete_community_indirect.py ./
COPY delete_community_evaluate.py delete_community_leiden.py delete_community_unique.py ./
COPY delete_community_merge.py delete_community_update_graphml.py ./
COPY delete_community_update_ndoe_cluster.py delete_community_update_reports.py ./
COPY delete_community_update_reports_last.py delete_generate_graphml.py ./
COPY before_search.py fuzzing_match.py rag_match.py ./
COPY "delete all.py" ./
COPY setup.py readme.md ./

# 安装项目本身
RUN pip install --no-cache-dir -e .

ENTRYPOINT ["python", "delete all.py"]
