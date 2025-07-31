from embedding import EmbeddingManager


class EmbeddingRetrieverWrapper:
    def __init__(self, embedding_manager: EmbeddingManager):
        self.embedding_manager = embedding_manager

    def get_relevant_documents(self, query: str):
        results = self.embedding_manager.search(query)
        return [r.to_langchain_document() for r in results]