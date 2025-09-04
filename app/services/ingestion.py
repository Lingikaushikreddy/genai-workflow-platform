from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class IngestionService:
    def __init__(self, vector_store, chunk_size: int, chunk_overlap: int):
        self.vector_store = vector_store
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def ingest(self, documents: list) -> dict:
        docs = [Document(page_content=d.text, metadata=d.metadata) for d in documents]
        chunks = self.splitter.split_documents(docs)
        if chunks:
            chunk_ids = self.vector_store.add_documents(chunks)
        else:
            chunk_ids = []
        return {
            "documents_received": len(docs),
            "chunks_ingested": len(chunks),
            "chunk_ids": chunk_ids
        }
