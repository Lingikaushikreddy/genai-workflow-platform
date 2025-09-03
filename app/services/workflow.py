import operator
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import END, StateGraph
import time
from app.models.schemas import WorkflowMetadata, Source

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    query: str
    context: str
    sources: list[Source]

class WorkflowEngine:
    def __init__(self, llm, vector_store, retrieval_k: int):
        self.llm = llm
        self.vector_store = vector_store
        self.retrieval_k = retrieval_k
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("generate", self._generate_node)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        return workflow.compile()

    def _retrieve_node(self, state: AgentState):
        docs = self.vector_store.similarity_search(state["query"], k=self.retrieval_k)
        context = "\n".join([doc.page_content for doc in docs])
        sources = [Source(content=doc.page_content, metadata=doc.metadata) for doc in docs]
        return {"context": context, "sources": sources}

    def _generate_node(self, state: AgentState):
        prompt = f"Answer based on context:\n\n{state['context']}\n\nQuery: {state['query']}"
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return {"messages": [response]}

    def run(self, query: str):
        state = {"query": query, "messages": [], "context": "", "sources": []}
        result = self.graph.invoke(state)
        return result
        
    async def stream(self, query: str):
        state = {"query": query, "messages": [], "context": "", "sources": []}
        # Simulating stream for mock
        yield {"event": "context", "data": {"sources": []}}
        yield {"event": "token", "data": {"token": "Generated token "}}
        yield {"event": "done", "data": {"status": "success"}}
