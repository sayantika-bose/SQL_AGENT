"""
Document Tool for retrieving information from indexed documents
"""
import requests
import logging
from typing import Dict, List, Any, Optional
from langchain.tools import BaseTool
from pydantic import Field
import threading

logger = logging.getLogger(__name__)


class DocumentTool(BaseTool):
    """Tool for querying indexed documents to answer user questions"""
    
    name: str = "document_search"
    description: str = """
    Search through indexed documents to find relevant information and answer questions.
    Use this tool when you need to find information from uploaded documents, PDFs, or other indexed content.
    
    Input should be a clear question or search query about the documents.
    The tool will return relevant information with source references.
    
    Examples:
    - "What are the main requirements mentioned in the project document?"
    - "Find information about database schema from the technical docs"
    - "What does the contract say about payment terms?"
    """
    
    indexer_base_url: str = Field(default="http://localhost:8002")
    max_results: int = Field(default=5)
    access_level: str = Field(default="administrator")
    
    def _update_progress(self, message: str):
        """Update task progress if running in Celery context"""
        try:
            # Try to get current task context
            from celery import current_task
            if current_task and hasattr(current_task, 'update_state'):
                current_task.update_state(
                    state='PROGRESS',
                    meta={'progress_message': message}
                )
                logger.info(f"Progress updated: {message}")
        except Exception:
            # Not in Celery context or update failed, just log
            logger.debug(f"Progress: {message}")
            pass
    
    def _run(self, query: str) -> str:
        """
        Execute document search and return formatted results
        
        Args:
            query: User's question or search query
            
        Returns:
            Formatted response with answer and source references
        """
        try:
            logger.info(f"Document search query: {query}")
            
            # Update progress if we have access to task context
            self._update_progress("🔍 Searching through indexed documents...")
            
            # Call the indexer's search endpoint
            search_results = self._search_documents(query)
            
            if not search_results or not search_results.get("results"):
                return "No relevant documents found for your query. Please make sure documents are indexed or try rephrasing your question."
            
            # Update progress
            self._update_progress("📄 Analyzing document content and extracting relevant information...")
            
            # Format the response with context and references
            # This now returns both the formatted response and the files actually used
            formatted_response, files_used_in_response = self._format_search_results(query, search_results)
            
            # Store filenames in a way that can be extracted by the master agent
            # Use only the files that were actually used in the response
            filenames_marker = f"\n\n__DOCUMENT_REFERENCES__: {','.join(files_used_in_response)}"
            formatted_response += filenames_marker
            
            # Update progress
            self._update_progress("✅ Document analysis complete, preparing response...")
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Document tool error: {str(e)}")
            return f"Error searching documents: {str(e)}. Please check if the indexer service is running."
    
    async def _arun(self, query: str) -> str:
        """Async version of _run"""
        return self._run(query)
    
    def _extract_unique_filenames(self, search_results: Dict[str, Any]) -> List[str]:
        """
        Extract unique filenames from search results metadata
        
        Args:
            search_results: Results from indexer search
            
        Returns:
            List of unique filenames from the actual search results
        """
        unique_filenames = set()
        
        results = search_results.get("results", [])
        for result in results:
            metadata = result.get("metadata", {})
            filename = metadata.get("filename")
            if filename:
                unique_filenames.add(filename)
        
        return sorted(list(unique_filenames))
    
    def _search_documents(self, query: str) -> Dict[str, Any]:
        """
        Search documents using the indexer API
        
        Args:
            query: Search query
            
        Returns:
            Search results from indexer
        """
        try:
            search_url = f"{self.indexer_base_url}/api/v1/search"
            
            payload = {
                "query": query,
                "access_level": self.access_level,
                "max_results": self.max_results
            }
            
            response = requests.post(
                search_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Search API error: {response.status_code} - {response.text}")
                return {}
                
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to indexer at {self.indexer_base_url}")
            return {}
        except Exception as e:
            logger.error(f"Search request error: {str(e)}")
            return {}
    
    def _format_search_results(self, query: str, search_results: Dict[str, Any]) -> tuple[str, List[str]]:
        """
        Format search results into a comprehensive response
        
        Args:
            query: Original query
            search_results: Results from indexer
            
        Returns:
            Tuple of (formatted response string, list of files actually used in response)
        """
        try:
            results = search_results.get("results", [])
            total_count = search_results.get("total_count", 0)
            
            if not results:
                return "No relevant information found in the indexed documents.", []
            
            # Extract unique source files and organize content
            source_files = {}
            contexts = []
            
            for result in results:
                metadata = result.get("metadata", {})
                filename = metadata.get("filename", "Unknown")
                content = result.get("content", "")
                similarity_score = result.get("similarity_score", 0)
                chunk_index = metadata.get("chunk_index", 0)
                
                # Track source files with chunk counts
                if filename not in source_files:
                    source_files[filename] = []
                source_files[filename].append(chunk_index)
                
                contexts.append({
                    "content": content,
                    "filename": filename,
                    "score": similarity_score,
                    "chunk_index": chunk_index
                })
            
            # Build the response
            response_parts = []
            
            # Add main answer based on most relevant content
            response_parts.append("📄 **Document Search Results:**\n")
            
            # Group content by source file for better organization
            file_contents = {}
            for context in contexts:
                filename = context["filename"]
                if filename not in file_contents:
                    file_contents[filename] = []
                file_contents[filename].append(context)
            
            # Present information organized by source
            # Track which files actually contribute content to the response
            files_used_in_response = []
            
            for filename, file_contexts in file_contents.items():
                response_parts.append(f"**From: {filename}**")
                files_used_in_response.append(filename)
                
                # Show most relevant chunks from this file
                sorted_contexts = sorted(file_contexts, key=lambda x: x["score"], reverse=True)
                for i, context in enumerate(sorted_contexts[:2], 1):  # Top 2 chunks per file
                    response_parts.append(f"• {context['content']}")
                
                response_parts.append("")  # Empty line between files
            
            # Add comprehensive source references (only for files actually used)
            response_parts.append("📚 **Source Documents:**")
            for filename in files_used_in_response:
                chunk_count = len(source_files[filename])
                response_parts.append(f"• **{filename}** ({chunk_count} relevant section{'s' if chunk_count > 1 else ''})")
            
            # Add search metadata
            response_parts.append(f"\n🔍 **Search Summary:** Found {total_count} relevant sections from {len(files_used_in_response)} document(s)")
            
            return "\n".join(response_parts), files_used_in_response
            
        except Exception as e:
            logger.error(f"Error formatting results: {str(e)}")
            return f"Found relevant information but encountered formatting error: {str(e)}", []
    
    def get_document_status(self, filename: str) -> Dict[str, Any]:
        """
        Check if a specific document is indexed
        
        Args:
            filename: Name of the document to check
            
        Returns:
            Status information
        """
        try:
            status_url = f"{self.indexer_base_url}/api/v1/indexing/status/{filename}"
            response = requests.get(status_url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status check failed: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Status check error: {str(e)}"}
    
    def list_indexed_files(self) -> List[str]:
        """
        Get list of all indexed files
        
        Returns:
            List of indexed filenames
        """
        try:
            files_url = f"{self.indexer_base_url}/api/v1/management/files"
            response = requests.get(files_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("files", [])
            else:
                logger.error(f"Files list error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Files list error: {str(e)}")
            return []


def create_document_tool(
    indexer_url: str = "http://localhost:8002",
    max_results: int = 5,
    access_level: str = "administrator"
) -> DocumentTool:
    """
    Factory function to create a DocumentTool instance
    
    Args:
        indexer_url: Base URL of the indexer service
        max_results: Maximum number of search results
        access_level: Access level for document search
        
    Returns:
        Configured DocumentTool instance
    """
    return DocumentTool(
        indexer_base_url=indexer_url,
        max_results=max_results,
        access_level=access_level
    )