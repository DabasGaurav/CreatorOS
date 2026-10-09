"""Builds and compiles the LangGraph pipeline (B3 step 2): research -> opportunity
-> ranking -> baselines -> explore/exploit -> rerank -> content, per the edge
order given in the spec (research -> opportunity -> rank -> rerank -> generate),
with baseline logging and the deterministic explore/exploit selection inserted
between ranking and reranking — see nodes.rerank_node_factory's docstring
reference in content/reranker.py for why explore/exploit must run before, not
after, the LLM reranker.
"""

from langgraph.graph import END, START, StateGraph
from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from creatorsignal.graph.nodes import (
    baseline_node_factory,
    content_node_factory,
    explore_exploit_node,
    opportunity_node_factory,
    ranking_node_factory,
    rerank_node_factory,
    research_node_factory,
)
from creatorsignal.graph.state import GraphState


def build_pipeline(session: Session, qdrant: QdrantClient):
    graph = StateGraph(GraphState)

    graph.add_node("research", research_node_factory(session))
    graph.add_node("opportunity", opportunity_node_factory())
    graph.add_node("ranking", ranking_node_factory(session, qdrant))
    graph.add_node("baselines", baseline_node_factory())
    graph.add_node("explore_exploit", explore_exploit_node)
    graph.add_node("rerank", rerank_node_factory())
    graph.add_node("content", content_node_factory())

    graph.add_edge(START, "research")
    graph.add_edge("research", "opportunity")
    graph.add_edge("opportunity", "ranking")
    graph.add_edge("ranking", "baselines")
    graph.add_edge("baselines", "explore_exploit")
    graph.add_edge("explore_exploit", "rerank")
    graph.add_edge("rerank", "content")
    graph.add_edge("content", END)

    return graph.compile()
