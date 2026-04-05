"""
Vector Memory - Long-term vector storage for business research data.
Wraps ChromaDB with business-specific collections.
"""
import chromadb
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()


class VectorMemory:
    """Manages business-specific vector collections in ChromaDB."""
    
    def __init__(self):
        self.chroma_client = chromadb.Client()
        self.genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.embedding_model = "models/gemini-embedding-2-preview"
        
        # Business-specific collections
        self.research_collection = self.chroma_client.get_or_create_collection(
            name="business_research"
        )
        self.ideas_collection = self.chroma_client.get_or_create_collection(
            name="business_ideas"
        )
    
    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Gemini."""
        response = self.genai_client.models.embed_content(
            model=self.embedding_model,
            contents=texts
        )
        return [e.values for e in response.embeddings]
    
    def store_research(self, session_id: str, texts: list[str], metadatas: list[dict] = None):
        """Store research findings in the vector DB."""
        if not texts:
            return
        
        embeddings = self._embed(texts)
        ids = [f"{session_id}_research_{i}" for i in range(len(texts))]
        
        if metadatas is None:
            metadatas = [{"session_id": session_id, "type": "research"} for _ in texts]
        
        self.research_collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
    
    def store_idea(self, session_id: str, idea_text: str, metadata: dict = None):
        """Store a generated business idea."""
        embedding = self._embed([idea_text])
        idea_id = f"{session_id}_idea_{self.ideas_collection.count()}"
        
        self.ideas_collection.add(
            ids=[idea_id],
            embeddings=embedding,
            documents=[idea_text],
            metadatas=[metadata or {"session_id": session_id, "type": "idea"}]
        )
    
    def search_research(self, query: str, n_results: int = 5) -> list[dict]:
        """Search research collection."""
        if self.research_collection.count() == 0:
            return []
        
        query_embedding = self._embed([query])
        results = self.research_collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, self.research_collection.count())
        )
        
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        return [
            {"text": doc, "metadata": meta}
            for doc, meta in zip(documents, metadatas)
        ]
    
    def clear_session(self, session_id: str):
        """Clear all vectors for a given session."""
        # ChromaDB doesn't support filtering deletes well, so we just reset
        try:
            self.chroma_client.delete_collection(name="business_research")
            self.research_collection = self.chroma_client.get_or_create_collection(
                name="business_research"
            )
        except Exception:
            pass


# Global instance
vector_memory = VectorMemory()
