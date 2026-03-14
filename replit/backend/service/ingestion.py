from db.pinecone_db import PineconeDB
# from infra.mongo import get_collection_from_country  # Commented out MongoDB
import re
import uuid
from infra.logger import logger
from typing import Dict, Any

class IngestionService:
    def __init__(
            self,
            vector_db: PineconeDB = None,
            embedding_function = None):
        self.vector_db = vector_db
        self.embedding_function = embedding_function

    def load_text(self, file_path):
        """
        Loads text from a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The text from the file.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def split_text(self, text, chunk_size):
        """
        Splits text into chunks of a given size.

        Args:
            text (str): The text to split.
            chunk_size (int): The size of the chunks.

        Returns:
            list: A list of chunks.
        """
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    def sliding_window_split(self, text, window_size, overlap):
        """
        Splits text into chunks of a given size using a sliding window.

        Args:
            text (str): The text to split.
            window_size (int): The size of the window.
            overlap (int): The overlap between the windows.

        Returns:
            list: A list of chunks.
        """
        stride = window_size - overlap
        if stride <= 0:
            raise ValueError("Overlap must be smaller than window size.")
        chunks = []
        for i in range(0, len(text) - window_size + 1, stride):
            chunks.append(text[i:i+window_size])
        if len(text) > 0 and (len(text) - window_size) % stride != 0:
            chunks.append(text[-window_size:])
        return chunks
    
    
    def ingest_text_by_country(self, full_text: str, country_code: str, language: str = "en", party: str = "", chunk_size: int = 1024, chunk_overlap: int = 64, sliding_window: int = None) -> Dict[str, Any]:
        """
        Ingests text into Pinecone vector database using single-sized chunks with new metadata format.

        Args:
            full_text (str): The text content to ingest.
            country_code (str): The country code (e.g., "CA", "US").
            language (str): The language code (e.g., "en", "fr").
            party (str): The political party name.
            chunk_size (int): The size of the chunks.
            chunk_overlap (int): The overlap between chunks.
            sliding_window (int): Deprecated - not used in simplified architecture.
        """

        cleaned_full_text = re.sub(r'\n', ' ', full_text)  # remove "\n"
        
        # Use sliding window chunking directly (no parent-child structure)
        chunks = self.sliding_window_split(cleaned_full_text, chunk_size, chunk_overlap)
        
        all_documents = []
        all_embeddings = []
        all_ids = []
        all_metadatas = []

        # Generate document ID for this ingestion
        doc_id = str(uuid.uuid4())

        # Process each chunk individually with new metadata format
        for chunk_id, chunk in enumerate(chunks):
            # Limit chunk size to avoid Pinecone's message size limit
            # Pinecone limit is ~4MB, so let's keep chunks under 3000 characters to be safe
            if len(chunk) > 3000:
                logger.warning(f"Chunk {chunk_id} is {len(chunk)} chars, truncating to 3000")
                chunk = chunk[:3000]
            
            # Generate embeddings for each chunk
            chunk_embedding = self.embedding_function([chunk])
            
            all_documents.append(chunk)
            all_embeddings.append(chunk_embedding[0])  # Extract single embedding
            all_ids.append(f"{doc_id}::{chunk_id}")  # New ID format: doc_id::chunk_index
            all_metadatas.append({
                "doc_id": doc_id,
                "chunk_index": chunk_id,
                "country": country_code,  # Use country_code as the country value (e.g., "CA" instead of "Canada")
                "language": language,
                "party": party,
                "text": chunk  # Store the text in metadata for retrieval
            })
            
            logger.debug(f"Prepared chunk {chunk_id} for Pinecone ingestion ({len(chunk)} chars)")

        # Batch insert all documents into Pinecone
        if all_documents:
            self.vector_db.add_document_by_country(
                country=country_code,  # Use country_code instead of country
                documents=all_documents,
                embeddings=all_embeddings,
                ids=all_ids,
                metadatas=all_metadatas
            )
            logger.info(f"Ingested {len(all_documents)} chunks into Pinecone for country: {country_code}, party: {party}")
            
            # Verify ingestion by doing a quick query
            try:
                verification_result = self.vector_db.query(
                    query_embeddings=[all_embeddings[0]],  # Use first embedding
                    n_results=1,
                    country=country_code  # Use country_code for verification
                )
                verified_count = len(verification_result['documents'][0])
                logger.info(f"Verification: Found {verified_count} documents for country {country_code} in Pinecone")
            except Exception as e:
                logger.warning(f"Failed to verify ingestion for {country_code}: {e}")

        logger.info(f"Ingestion successful")
        
        return {
            'success': True,
            'total_chunks': len(chunks),
            'processed_chunks': len(all_documents)
        }