import os
from pypdf import PdfReader
import chromadb
import time
import traceback
import asyncio
from crawl4ai import AsyncWebCrawler
from urllib.parse import urlparse
from google import genai
from dotenv import load_dotenv

load_dotenv()

class RAGEngine:
    def __init__(self):
        # We use ephemeral client since the user wants memory to be temporary (per session)
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(name="perplexity_pdfs")
        
        # Initialize GenAI Client for embeddings
        self.genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.embedding_model = "models/gemini-embedding-2-preview"

    def _get_domain(self, url):
        try:
            return urlparse(url).netloc
        except:
            return "Web Source"

    def process_pdf(self, file_path, file_id):
        """Extracts text from PDF, chunks it, and adds to the vector store."""
        try:
            print(f"DEBUG: Processing file: {file_path}")
            # strict=False allows reading PDFs with minor formatting errors (common in academic/internship reports)
            reader = PdfReader(file_path, strict=False)
            text = ""
            print(f"DEBUG: Found {len(reader.pages)} pages in {file_id}")
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as pe:
                    print(f"DEBUG: Could not extract text from page {i}: {pe}")
            
            # Extract text from Pages
            if not text.strip():
                return False, "PDF might be image-only (no extractable text found)."
            
            return self._index_text(text, file_id, title=file_id, domain="Local PDF")
        except Exception as e:
            err_msg = f"ERROR: {str(e)}"
            print(f"ERROR processing PDF {file_id}: {err_msg}")
            traceback.print_exc()
            return False, err_msg

    async def process_url(self, url):
        """Crawls a URL, extracts Markdown, and adds to the vector store."""
        try:
            print(f"DEBUG: Crawling URL: {url}")
            
            async def crawl_and_index():
                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=url)
                    if not result.success:
                        return False, f"Crawl failed: {result.error_message}"
                    
                    markdown = result.markdown
                    if not markdown or len(markdown.strip()) < 10:
                        return False, "Crawl returned no significant content."
                    
                    # Store as a virtual file_id
                    file_id = f"web_{int(time.time())}_{url[:30]}"
                    
                    # Extract title, domain, and OG image
                    title = result.metadata.get('og:title') or result.metadata.get('title') or url
                    image = result.metadata.get('og:image') or result.metadata.get('image')
                    domain = self._get_domain(url)
                    
                    return self._index_text(markdown, file_id, title=title, domain=domain, image=image)

            return await crawl_and_index()
            
        except Exception as e:
            err_msg = f"ERROR: {str(e)}"
            print(f"ERROR crawling URL {url}: {err_msg}")
            traceback.print_exc()
            return False, err_msg

    def _index_text(self, text, file_id, title=None, domain=None, image=None):
        """Helper to chunk and index raw text with enhanced metadata."""
        try:
            # Smaller chunk size for much finer-grained and accurate retrieval
            chunk_size = 1000
            overlap = 200
            chunks = []
            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i:i + chunk_size]
                if chunk and len(chunk.strip()) > 5:
                    chunks.append(chunk)

            if not chunks:
                return False, "Could not segment the content into valid text chunks."

            print(f"DEBUG: Generating {len(chunks)} chunks from {file_id}. Embedding...")

            all_embeddings = []
            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                try:
                    embeddings_response = self.genai_client.models.embed_content(
                        model=self.embedding_model,
                        contents=batch
                    )
                    all_embeddings.extend([e.values for e in embeddings_response.embeddings])
                except Exception as ex:
                    if "429" in str(ex):
                        print("DEBUG: Quota hit during embedding. Sleeping for 65 seconds...")
                        time.sleep(65)
                        embeddings_response = self.genai_client.models.embed_content(
                            model=self.embedding_model,
                            contents=batch
                        )
                        all_embeddings.extend([e.values for e in embeddings_response.embeddings])
                    else:
                        raise ex
            
            ids = [f"{file_id}_{i}" for i in range(len(chunks))]
            
            # Enrich metadatas for the cards
            metadatas = []
            for i, chunk in enumerate(chunks):
                metadatas.append({
                    "source": file_id,
                    "title": title or file_id,
                    "domain": domain or "Local Source",
                    "image": image or "",
                    "snippet": chunk[:150] + "..." # Snippet for the card preview
                })

            self.collection.add(
                ids=ids,
                embeddings=all_embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            print(f"DEBUG: Successfully indexed {file_id}")
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def retrieve_context_with_sources(self, query, n_results=5):
        """Retrieves relevant text chunks and their sources."""
        try:
            # Check if collection is empty
            if self.collection.count() == 0:
                print("DEBUG: Search performed on empty vector collection.")
                return []
                
            # Generate embedding for the query
            query_embedding = self.genai_client.models.embed_content(
                model=self.embedding_model,
                contents=[query]
            ).embeddings[0].values

            # Query the vector store
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count())
            )

            # Extract documents and metadatas
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            
            context_items = []
            for doc, meta in zip(documents, metadatas):
                context_items.append({
                    "text": doc,
                    "source": meta.get("source", "Unknown Source"),
                    "title": meta.get("title", "Unknown Title"),
                    "domain": meta.get("domain", "Unknown Domain"),
                    "snippet": meta.get("snippet", "")
                })
            
            return context_items
        except Exception as e:
            print(f"Error retrieving context for query '{query}': {e}")
            return []

    def clear(self):
        """Clears the collection."""
        self.chroma_client.delete_collection(name="perplexity_pdfs")
        self.collection = self.chroma_client.get_or_create_collection(name="perplexity_pdfs")

# Global instances can be used across the app
rag_engine = RAGEngine()
