"""
OpenSearch vector database connection and management with Ollama
"""
from opensearchpy import OpenSearch
import requests
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
import uuid

from indexer.src.core.config import get_settings

logger = logging.getLogger(__name__)


class VectorDatabase:
    """OpenSearch vector database manager"""
    
    def __init__(self):
        """Initialize OpenSearch vector database"""
        self.settings = get_settings()
        self._client = None
        self._setup_database()
        
    def _setup_database(self):
        """Setup OpenSearch vector database with Ollama embeddings"""
        try:
            # Initialize OpenSearch client
            opensearch_url = getattr(self.settings, 'opensearch_url', 'http://localhost:9200')
            self._client = OpenSearch(
                hosts=[opensearch_url],
                http_auth=getattr(self.settings, 'opensearch_auth', None),
                use_ssl=getattr(self.settings, 'opensearch_use_ssl', False),
                verify_certs=getattr(self.settings, 'opensearch_verify_certs', False),
                ssl_assert_hostname=False,
                ssl_show_warn=False,
            )
            
            # Test connection
            info = self._client.info()
            logger.info(f"Connected to OpenSearch: {info['version']['number']}")
            
            # Create index if it doesn't exist
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            self._create_index_if_not_exists(index_name)
            
            logger.info(f"OpenSearch vector database initialized with index: {index_name}")
            logger.info(f"Using Ollama embeddings model: {self.settings.ollama_model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch vector database: {str(e)}")
            # Set client to None to indicate unavailable state
            self._client = None
            raise
    
    def _create_index_if_not_exists(self, index_name: str):
        """Create OpenSearch index with vector field mapping if it doesn't exist"""
        try:
            if not self._client.indices.exists(index=index_name):
                # Index mapping for vector search
                mapping = {
                    "mappings": {
                        "properties": {
                            "content": {
                                "type": "text",
                                "analyzer": "standard"
                            },
                            "vector": {
                                "type": "knn_vector",
                                "dimension": 768,  # nomic-embed-text embedding dimension
                                "method": {
                                    "name": "hnsw",
                                    "space_type": "cosinesimil",
                                    "engine": "lucene"
                                }
                            },
                            "metadata": {
                                "type": "object",
                                "properties": {
                                    "chunk_id": {"type": "keyword"},
                                    "filename": {"type": "keyword"},
                                    "file_type": {"type": "keyword"},
                                    "access_level": {"type": "keyword"},
                                    "chunk_index": {"type": "integer"},
                                    "chunk_size": {"type": "integer"},
                                    "created_at": {"type": "date"}
                                }
                            }
                        }
                    },
                    "settings": {
                        "index": {
                            "knn": True,
                            "knn.algo_param.ef_search": 100
                        }
                    }
                }
                
                self._client.indices.create(index=index_name, body=mapping)
                logger.info(f"Created OpenSearch index: {index_name}")
            else:
                logger.info(f"OpenSearch index already exists: {index_name}")
                
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama API"""
        try:
            logger.debug(f"Requesting embedding for text: {text[:100]}...")
            response = requests.post(
                f"{self.settings.ollama_base_url}/api/embeddings",
                json={
                    "model": self.settings.ollama_model,
                    "prompt": text
                },
                timeout=30
            )
            logger.debug(f"Ollama API response status: {response.status_code}")
            if response.status_code == 404:
                logger.error(f"Ollama model '{self.settings.ollama_model}' not found. Please run: ollama pull {self.settings.ollama_model}")
                raise ValueError(f"Ollama model '{self.settings.ollama_model}' not found")
            response.raise_for_status()
            result = response.json()
            if "embedding" not in result:
                logger.error(f"No embedding in response: {result}")
                raise ValueError("No embedding returned from Ollama")
            embedding = result["embedding"]
            if not embedding or len(embedding) == 0:
                logger.error("Empty embedding returned from Ollama")
                raise ValueError("Empty embedding returned")
            logger.debug(f"Successfully generated embedding with dimension: {len(embedding)}")
            return embedding
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to Ollama at {self.settings.ollama_base_url}. Is Ollama running?")
            raise ConnectionError(f"Cannot connect to Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to get embedding: {str(e)}")
            raise
    
    @property
    def client(self):
        """Get OpenSearch client"""
        return self._client
    
    def is_available(self) -> bool:
        """Check if the vector database is available"""
        return self._client is not None
    
    def _check_availability(self):
        """Check if database is available and raise appropriate error"""
        if not self.is_available():
            raise ConnectionError(
                "Vector database is not available. "
                "Please ensure OpenSearch is running and properly configured."
            )
    
    def add_chunks(
        self,
        chunk_ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> bool:
        """
        Add document chunks to the vector database
        
        Args:
            chunk_ids: List of unique chunk identifiers
            documents: List of chunk content
            metadatas: List of metadata dictionaries for each chunk
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._check_availability()
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            
            # Process documents in batches
            for chunk_id, document, metadata in zip(chunk_ids, documents, metadatas):
                # Get embedding for the document
                vector = self._get_embedding(document)
                
                # Prepare document for indexing
                doc = {
                    "content": document,
                    "vector": vector,
                    "metadata": {**metadata, 'chunk_id': chunk_id}
                }
                
                # Index document
                self._client.index(
                    index=index_name,
                    id=chunk_id,
                    body=doc
                )
            
            # Refresh index to make documents searchable
            self._client.indices.refresh(index=index_name)
            
            logger.info(f"Added {len(chunk_ids)} chunks to OpenSearch index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add chunks: {str(e)}")
            return False
    
    def search_chunks(
        self,
        query_text: str,
        access_level: str,
        n_results: int = 10,
        where_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for relevant chunks with access control
        
        Args:
            query_text: Search query
            access_level: User's access level for filtering
            n_results: Maximum number of results to return
            where_filters: Additional metadata filters
            
        Returns:
            Search results dictionary
        """
        try:
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            
            # Get query embedding
            query_vector = self._get_embedding(query_text)
            
            # Build filter conditions
            filter_conditions = [
                {"term": {"metadata.access_level": access_level}}
            ]
            
            if where_filters:
                for key, value in where_filters.items():
                    filter_conditions.append({"term": {f"metadata.{key}": value}})
            
            # Build OpenSearch query
            search_body = {
                "size": n_results,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "vector": {
                                        "vector": query_vector,
                                        "k": n_results
                                    }
                                }
                            }
                        ],
                        "filter": filter_conditions
                    }
                },
                "_source": ["content", "metadata"]
            }
            
            # Execute search
            response = self._client.search(index=index_name, body=search_body)
            
            if not response['hits']['hits']:
                return {
                    "success": True,
                    "results": {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]},
                    "count": 0
                }
            
            # Format results
            ids = []
            documents = []
            metadatas = []
            distances = []
            
            for hit in response['hits']['hits']:
                chunk_id = hit['_source']['metadata']['chunk_id']
                content = hit['_source']['content']
                metadata = {k: v for k, v in hit['_source']['metadata'].items() if k != 'chunk_id'}
                score = hit['_score']
                
                ids.append(chunk_id)
                documents.append(content)
                metadatas.append(metadata)
                distances.append(float(score))
            
            formatted_results = {
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
                "distances": [distances]
            }
            
            return {
                "success": True,
                "results": formatted_results,
                "count": len(response['hits']['hits'])
            }
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "results": None,
                "count": 0
            }
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific chunk by ID
        
        Args:
            chunk_id: Unique chunk identifier
            
        Returns:
            Chunk data or None if not found
        """
        try:
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            
            # Get document by ID
            response = self._client.get(index=index_name, id=chunk_id)
            
            if not response['found']:
                return None
            
            source = response['_source']
            metadata = {k: v for k, v in source['metadata'].items() if k != 'chunk_id'}
            
            return {
                "id": chunk_id,
                "document": source['content'],
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {str(e)}")
            return None
    
    def delete_chunks(self, chunk_ids: List[str]) -> bool:
        """
        Delete chunks by IDs
        
        Args:
            chunk_ids: List of chunk IDs to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete documents from OpenSearch by chunk_id
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            
            for chunk_id in chunk_ids:
                # Search for documents with this chunk_id
                query = {
                    "query": {
                        "term": {
                            "metadata.chunk_id": chunk_id
                        }
                    }
                }
                
                # Delete by query
                self._client.delete_by_query(
                    index=index_name,
                    body=query
                )
            
            logger.info(f"Deleted {len(chunk_ids)} chunks from OpenSearch")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chunks: {str(e)}")
            return False
    
    def delete_by_filename(self, filename: str) -> bool:
        """
        Delete all chunks from a specific file
        
        Args:
            filename: Name of the file to delete chunks for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete documents from OpenSearch by filename
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            
            query = {
                "query": {
                    "term": {
                        "metadata.filename": filename
                    }
                }
            }
            
            # Delete by query
            result = self._client.delete_by_query(
                index=index_name,
                body=query
            )
            
            deleted_count = result.get('deleted', 0)
            logger.info(f"Deleted {deleted_count} chunks for file: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chunks from {filename}: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            if not self.is_available():
                return {
                    "success": False,
                    "error": "Vector database not available",
                    "total_chunks": 0
                }
            
            # Get index stats from OpenSearch
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            
            # Get document count
            count_result = self._client.count(index=index_name)
            total_chunks = count_result['count']
            
            return {
                "success": True,
                "total_chunks": total_chunks,
                "collection_name": index_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_chunks": 0
            }
    
    def list_files(self, access_level: Optional[str] = None) -> List[str]:
        """
        List all unique filenames in the collection
        
        Args:
            access_level: Optional access level filter
            
        Returns:
            List of unique filenames
        """
        try:
            if not self.is_available():
                return []
            
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            
            # Build query with optional access level filter
            query = {
                "size": 0,  # We only want aggregations, not documents
                "aggs": {
                    "unique_files": {
                        "terms": {
                            "field": "metadata.filename",
                            "size": 10000  # Adjust based on expected number of files
                        }
                    }
                }
            }
            
            logger.debug(f"DEBUG: list_files query = {query}")
            
            # Add access level filter if specified
            if access_level:
                query["query"] = {
                    "term": {
                        "metadata.access_level": access_level
                    }
                }
            
            # Execute search
            response = self._client.search(index=index_name, body=query)
            
            # Extract filenames from aggregation results
            filenames = []
            if 'aggregations' in response and 'unique_files' in response['aggregations']:
                buckets = response['aggregations']['unique_files']['buckets']
                filenames = [bucket['key'] for bucket in buckets]
            
            logger.debug(f"Found {len(filenames)} unique files")
            return filenames
            
        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            return []

    def get_chunk_count_by_filename(self, filename: str) -> int:
        """
        Get the number of chunks for a specific filename
        
        Args:
            filename: Name of the file
            
        Returns:
            Number of chunks for the file
        """
        try:
            if not self.is_available():
                return 0
            
            index_name = getattr(self.settings, 'opensearch_index', 'documents')
            
            # Count documents with this filename
            query = {
                "query": {
                    "term": {
                        "metadata.filename": filename
                    }
                }
            }
            
            result = self._client.count(index=index_name, body=query)
            chunk_count = result['count']
            
            logger.debug(f"File '{filename}' has {chunk_count} chunks")
            return chunk_count
            
        except Exception as e:
            logger.error(f"Failed to get chunk count for {filename}: {str(e)}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the vector database
        
        Returns:
            Health status dictionary
        """
        try:
            if not self.is_available():
                return {
                    "status": "unhealthy",
                    "opensearch": "disconnected",
                    "ollama": "unknown",
                    "error": "OpenSearch client not initialized"
                }
            
            # Check OpenSearch
            opensearch_status = "healthy"
            try:
                info = self._client.info()
                opensearch_version = info['version']['number']
            except Exception as e:
                opensearch_status = f"unhealthy: {str(e)}"
                opensearch_version = "unknown"
            
            # Check Ollama
            ollama_status = "healthy"
            try:
                # Test embedding generation
                test_embedding = self._get_embedding("test")
                if not test_embedding or len(test_embedding) == 0:
                    ollama_status = "unhealthy: empty embedding returned"
            except Exception as e:
                ollama_status = f"unhealthy: {str(e)}"
            
            overall_status = "healthy" if opensearch_status == "healthy" and ollama_status == "healthy" else "unhealthy"
            
            return {
                "status": overall_status,
                "opensearch": opensearch_status,
                "opensearch_version": opensearch_version,
                "ollama": ollama_status,
                "ollama_url": self.settings.ollama_base_url,
                "ollama_model": self.settings.ollama_model
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    



# Global database instance
_db_instance: Optional[VectorDatabase] = None


def get_vector_db() -> VectorDatabase:
    """
    Get vector database instance (singleton)
    
    Returns:
        VectorDatabase instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = VectorDatabase()
        logger.info("Vector database connection initialized")
    return _db_instance


def init_vector_db():
    """Initialize vector database connection"""
    db = get_vector_db()
    logger.info("Vector database initialized")
    return db