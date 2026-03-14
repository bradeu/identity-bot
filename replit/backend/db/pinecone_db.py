from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
import uuid
from config.config import get_settings

# Country name to country code mapping
COUNTRY_NAME_TO_CODE = {
    'united states': 'US',
    'canada': 'CA', 
    'united kingdom': 'GB',
    'germany': 'DE',
    'france': 'FR',
    'japan': 'JP',
    'australia': 'AU',
    'brazil': 'BR',
    'india': 'IN',
    'china': 'CN',
    'mexico': 'MX',
    'italy': 'IT',
    'spain': 'ES',
    'netherlands': 'NL',
    'sweden': 'SE',
    'norway': 'NO',
    'switzerland': 'CH',
    'austria': 'AT',
    'belgium': 'BE',
    'denmark': 'DK'
}

class PineconeDB:
    def __init__(self, api_key: str, index_name: str = "bppl-rag"):
        """
        Initialize Pinecone client and index.
        
        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
        """
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.dimension = 1536  # OpenAI text-embedding-ada-002 dimension
        
        # Create index if it doesn't exist
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index_exists(self):
        """Create index if it doesn't exist"""
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )

    def heartbeat(self):
        """Health check for Pinecone connection"""
        try:
            self.pc.list_indexes()
            return True
        except Exception:
            return False
    
    def _normalize_country(self, country: str) -> str:
        """
        Convert country name to country code for consistent filtering.
        Supports both full names (e.g., "Canada") and codes (e.g., "CA").
        """
        if not country:
            return country
            
        # If it's already a 2-letter code, return as-is
        if len(country) == 2 and country.isupper():
            return country
            
        # Convert full name to code
        country_lower = country.lower().strip()
        return COUNTRY_NAME_TO_CODE.get(country_lower, country)

    def add_document_by_country(
        self,
        country: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> None:
        """
        Add documents to Pinecone index with country-specific metadata.
        
        Args:
            country: Country name for filtering
            documents: List of document texts
            embeddings: List of document embeddings
            metadatas: List of metadata dicts
            ids: List of document IDs
        """
        if not ids:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        if not metadatas:
            metadatas = [{} for _ in documents]
        
        # Add country to metadata for filtering
        for metadata in metadatas:
            # If country field is not already set, use the country parameter
            if 'country' not in metadata:
                metadata['country'] = country
        
        # Prepare vectors for upsert
        vectors = []
        for i, (doc_id, embedding, metadata) in enumerate(zip(ids, embeddings, metadatas)):
            # Only add text to metadata if it's not already there (new format includes it)
            if 'text' not in metadata:
                metadata['text'] = documents[i]  # Store original text in metadata
            
            vectors.append({
                'id': doc_id,
                'values': embedding,
                'metadata': metadata
            })
        
        # Upsert to Pinecone
        self.index.upsert(vectors=vectors)

    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        country: str = "Canada",
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query Pinecone for similar documents.
        
        Args:
            query_embeddings: List of query embeddings
            n_results: Number of results to return
            country: Country to filter by
            metadata_filter: Additional metadata filters
            
        Returns:
            Dict containing query results
        """
        # Build filter - normalize country to country code
        normalized_country = self._normalize_country(country)
        filter_dict = {'country': normalized_country}
        if metadata_filter:
            filter_dict.update(metadata_filter)
        
        query_embedding = query_embeddings[0] if query_embeddings else []
        
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        
        results = self.index.query(
            vector=query_embedding,
            top_k=n_results,
            filter=filter_dict,
            include_metadata=True
        )
        
        formatted_results = {
            'ids': [[]],
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }
        
        for match in results.matches:
            formatted_results['ids'][0].append(match.id)
            formatted_results['documents'][0].append(match.metadata.get('text', ''))
            formatted_results['metadatas'][0].append({
                k: v for k, v in match.metadata.items() if k != 'text'
            })
            formatted_results['distances'][0].append(1 - match.score)  # Convert similarity to distance
        
        return formatted_results

    def delete_country_collection(self, country: str) -> None:
        """
        Delete all documents for a specific country.
        
        Args:
            country: Country name to delete
        """
        # Normalize country to country code
        normalized_country = self._normalize_country(country)
        
        # Query all document IDs for the country
        query_results = self.index.query(
            vector=[0.0] * self.dimension,  # Dummy vector
            top_k=10000,  # Max limit
            filter={'country': normalized_country},
            include_metadata=False
        )
        
        # Delete all matching IDs
        if query_results.matches:
            ids_to_delete = [match.id for match in query_results.matches]
            self.index.delete(ids=ids_to_delete)

    def flush_all_collections(self) -> None:
        """
        Delete all documents from Pinecone index.
        """
        self.index.delete(delete_all=True)

    def count(self, country: Optional[str] = None) -> int:
        """
        Get document count for a country or total.
        
        Args:
            country: Country to count, None for total
            
        Returns:
            Number of documents
        """
        # Pinecone doesn't have a direct count method
        # We'll query with a dummy vector to get count
        normalized_country = self._normalize_country(country) if country else None
        filter_dict = {'country': normalized_country} if normalized_country else None
        
        results = self.index.query(
            vector=[0.0] * self.dimension,
            top_k=1,
            filter=filter_dict,
            include_metadata=False
        )
        
        # This is an approximation - Pinecone doesn't provide exact counts easily
        return len(results.matches) if results.matches else 0