from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.vectorstores import VectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore


class MockChatModel(BaseChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = AIMessage(
            content="Mock response. Your query was received successfully."
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"


class MockVectorStore(VectorStore):
    def add_texts(self, texts, metadatas=None, **kwargs):
        return ["mock-id"] * len(texts)

    def similarity_search(self, query: str, k: int = 4, **kwargs):
        return [
            Document(
                page_content="This is a mock retrieved document containing information about the platform.",
                metadata={"source": "mock"},
            )
        ]

    @classmethod
    def from_texts(cls, texts, embedding=None, metadatas=None, **kwargs):
        store = cls()
        store.add_texts(texts, metadatas)
        return store


class Providers:
    def __init__(self, llm: BaseChatModel, vector_store: VectorStore, mock_mode: bool):
        self.llm = llm
        self.vector_store = vector_store
        self.mock_mode = mock_mode


def build_providers(settings) -> Providers:
    mock_mode = not (settings.OPENAI_API_KEY and settings.PINECONE_API_KEY)

    if mock_mode:
        llm = MockChatModel()
        vector_store = MockVectorStore()
    else:
        # Since SecretStr is used for API keys in Settings
        openai_key = (
            settings.OPENAI_API_KEY.get_secret_value()
            if settings.OPENAI_API_KEY
            else None
        )
        pinecone_key = (
            settings.PINECONE_API_KEY.get_secret_value()
            if settings.PINECONE_API_KEY
            else None
        )

        llm = ChatOpenAI(api_key=openai_key, model=settings.OPENAI_MODEL)
        embeddings = OpenAIEmbeddings(
            api_key=openai_key, model=settings.OPENAI_EMBEDDING_MODEL
        )
        vector_store = PineconeVectorStore(
            index_name=settings.PINECONE_INDEX_NAME,
            embedding=embeddings,
            pinecone_api_key=pinecone_key,
        )

    return Providers(llm=llm, vector_store=vector_store, mock_mode=mock_mode)
