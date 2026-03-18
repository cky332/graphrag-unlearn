from .gdb_networkx import NetworkXStorage
from .vdb_hnswlib import HNSWVectorStorage
from .vdb_nanovectordb import NanoVectorDBStorage
from .kv_json import JsonKVStorage


def __getattr__(name):
    if name == "Neo4jStorage":
        from .gdb_neo4j import Neo4jStorage
        return Neo4jStorage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
