"""
Router modules for the Indexer service API endpoints
"""

from indexer.src.routers import indexing, search, management

__all__ = ["indexing", "search", "management"]