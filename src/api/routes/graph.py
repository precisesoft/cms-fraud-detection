"""Evidence graph endpoint — returns nodes and edges for a provider."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.graph_client import get_graph_db
from src.api.schemas import GraphEdge, GraphNode, GraphResponse

router = APIRouter(prefix="/graph", tags=["graph"])

# ---------------------------------------------------------------------------
# Cypher — fetch the full subgraph for one provider
# ---------------------------------------------------------------------------

_GRAPH_CYPHER = """
MATCH (p:Provider {npi: $npi})
OPTIONAL MATCH (p)-[hc:HAS_CASE]->(c:Case)
OPTIONAL MATCH (c)-[hs:HAS_SIGNAL]->(s:Signal)
OPTIONAL MATCH (c)-[ip:IN_PEER_GROUP]->(pg:PeerGroup)
OPTIONAL MATCH (s)-[sf:SOURCED_FROM]->(src:Source)
OPTIONAL MATCH (p)-[sz:SAME_ZIP]-(neighbor:Provider)
RETURN p, hc, c, hs, s, ip, pg, sf, src, sz, neighbor
"""


def _node_id(node) -> str:  # type: ignore[no-untyped-def]
    """Build a stable string ID from a Neo4j node."""
    labels = list(node.labels)
    node_type = labels[0] if labels else "Unknown"
    props = dict(node)
    if node_type == "Provider":
        return f"provider:{props.get('npi', '')}"
    if node_type == "Case":
        return f"case:{props.get('case_id', '')}"
    if node_type == "Signal":
        return f"signal:{props.get('name', '')}"
    if node_type == "PeerGroup":
        return f"peergroup:{props.get('key', '')}"
    if node_type == "Source":
        return f"source:{props.get('dataset', '')}"
    return f"{node_type.lower()}:{node.element_id}"


def _node_label(node) -> str:  # type: ignore[no-untyped-def]
    """Build a human-readable label for a Neo4j node."""
    labels = list(node.labels)
    node_type = labels[0] if labels else "Unknown"
    props = dict(node)
    if node_type == "Provider":
        return str(props.get("name") or props.get("npi") or "")
    if node_type == "Case":
        return str(props.get("hcpcs_cd") or props.get("case_id") or "")
    if node_type == "Signal":
        return str(props.get("name") or "")
    if node_type == "PeerGroup":
        return f"{props.get('specialty', '')} / {props.get('hcpcs_cd', '')}"
    if node_type == "Source":
        return str(props.get("dataset") or "")
    return str(props)


def _build_graph(records: list) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Convert Neo4j result records into deduplicated node and edge lists."""
    nodes_map: dict[str, GraphNode] = {}
    edges_set: set[tuple[str, str, str]] = set()
    edges: list[GraphEdge] = []

    def add_node(node) -> str | None:  # type: ignore[no-untyped-def]
        if node is None:
            return None
        nid = _node_id(node)
        if nid not in nodes_map:
            labels = list(node.labels)
            nodes_map[nid] = GraphNode(
                id=nid,
                type=labels[0] if labels else "Unknown",
                label=_node_label(node),
                properties=dict(node),
            )
        return nid

    def add_edge(source_id: str | None, target_id: str | None, rel) -> None:  # type: ignore[no-untyped-def]
        if source_id is None or target_id is None or rel is None:
            return
        rel_type = rel.type
        edge_key = (source_id, target_id, rel_type)
        if edge_key not in edges_set:
            edges_set.add(edge_key)
            edges.append(
                GraphEdge(
                    source=source_id,
                    target=target_id,
                    type=rel_type,
                    properties=dict(rel),
                )
            )

    for record in records:
        p_id = add_node(record.get("p"))
        c_id = add_node(record.get("c"))
        s_id = add_node(record.get("s"))
        pg_id = add_node(record.get("pg"))
        src_id = add_node(record.get("src"))

        neighbor_id = add_node(record.get("neighbor"))

        add_edge(p_id, c_id, record.get("hc"))
        add_edge(c_id, s_id, record.get("hs"))
        add_edge(c_id, pg_id, record.get("ip"))
        add_edge(s_id, src_id, record.get("sf"))
        add_edge(p_id, neighbor_id, record.get("sz"))

    return list(nodes_map.values()), edges


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/{npi}", response_model=GraphResponse)
async def get_evidence_graph(
    npi: str,
    session=Depends(get_graph_db),  # type: ignore[no-untyped-def]
) -> GraphResponse:
    """Return the evidence graph (nodes + edges) for a given provider NPI."""
    result = await session.run(_GRAPH_CYPHER, npi=npi)
    records = await result.fetch(1000)

    # Each record is a Neo4j Record; access values by key to get Node/Relationship objects
    record_dicts = [dict(record) for record in records]

    if not record_dicts or record_dicts[0].get("p") is None:
        raise HTTPException(status_code=404, detail=f"Provider {npi} not found in graph")

    nodes, edges = _build_graph(record_dicts)
    return GraphResponse(npi=npi, nodes=nodes, edges=edges)
