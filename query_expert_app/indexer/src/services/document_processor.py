"""
Document processing service for loading, chunking, and embedding documents
"""
import os
import uuid
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import time
from datetime import datetime

# Document processing libraries
import PyPDF2
import docx
import pandas as pd
from io import StringIO

# OCR libraries
try:
    import pytesseract
    import fitz  # PyMuPDF
    from PIL import Image
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OCR libraries not available: {e}. Image-based PDFs will not be processed.")
    OCR_AVAILABLE = False

from indexer.src.core.config import get_settings
from indexer.src.core.vector_db import get_vector_db
from indexer.src.models.schemas import (
    DocumentMetadata, 
    ChunkMetadata, 
    DocumentChunk, 
    FileType, 
    AccessLevel
)

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing documents into chunks and embeddings"""
    
    def __init__(self):
        """Initialize document processor"""
        self.settings = get_settings()
        self.vector_db = get_vector_db()
        
        # Ensure upload directory exists
        self.upload_dir = Path(self.settings.upload_directory)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Document processing methods mapping
        self.processors = {
            FileType.PDF: self._process_pdf,
            FileType.TXT: self._process_text,
            FileType.DOCX: self._process_docx,
            FileType.XLSX: self._process_excel,
            FileType.CSV: self._process_csv,
            FileType.MD: self._process_text
        }
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not file_path.exists():
                return False, "File does not exist"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.settings.max_file_size_bytes:
                max_mb = self.settings.max_file_size_mb
                return False, f"File size exceeds maximum allowed size of {max_mb}MB"
            
            # Check file extension
            file_extension = file_path.suffix.lower().lstrip('.')
            if file_extension not in self.settings.allowed_extensions_list:
                allowed = ", ".join(self.settings.allowed_extensions_list)
                return False, f"File type '{file_extension}' not allowed. Supported types: {allowed}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False, f"File validation failed: {str(e)}"
    
    def detect_file_type(self, filename: str) -> Optional[FileType]:
        """
        Detect file type from filename
        
        Args:
            filename: Name of the file
            
        Returns:
            FileType enum or None if not supported
        """
        extension = Path(filename).suffix.lower().lstrip('.')
        
        type_mapping = {
            'pdf': FileType.PDF,
            'txt': FileType.TXT,
            'docx': FileType.DOCX,
            'xlsx': FileType.XLSX,
            'csv': FileType.CSV,
            'md': FileType.MD
        }
        
        return type_mapping.get(extension)
    
    def _process_pdf(self, file_path: Path) -> List[str]:
        """Process PDF file and extract text using multiple methods"""
        content_pages = []
        
        try:
            # Method 1: Try PyMuPDF first (faster and more reliable)
            if OCR_AVAILABLE:
                content_pages = self._process_pdf_with_pymupdf(file_path)
                if content_pages:
                    logger.info(f"Successfully extracted text using PyMuPDF from {file_path.name}")
                    return content_pages
            
            # Method 2: Fallback to PyPDF2 for text-based PDFs
            content_pages = self._process_pdf_with_pypdf2(file_path)
            if content_pages:
                logger.info(f"Successfully extracted text using PyPDF2 from {file_path.name}")
                return content_pages
            
            # Method 3: If no text found, try OCR on images
            if OCR_AVAILABLE:
                logger.info(f"No text found in {file_path.name}, attempting OCR extraction...")
                content_pages = self._process_pdf_with_ocr(file_path)
                if content_pages:
                    logger.info(f"Successfully extracted text using OCR from {file_path.name}")
                    return content_pages
            
            # If all methods fail
            logger.warning(f"No text could be extracted from {file_path.name} using any method")
            return []
                
        except Exception as e:
            logger.error(f"Error processing PDF {file_path.name}: {str(e)}")
            return []
    
    def _process_pdf_with_pymupdf(self, file_path: Path) -> List[str]:
        """Extract text using PyMuPDF (handles both text and some image-based content)"""
        content_pages = []
        try:
            doc = fitz.open(str(file_path))
            
            # Check if PDF is encrypted
            if doc.needs_pass:
                logger.warning(f"PDF file {file_path.name} is encrypted/password-protected")
                doc.close()
                return []
            
            total_pages = len(doc)
            logger.info(f"Processing PDF with PyMuPDF: {total_pages} pages")
            
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    text = page.get_text()
                    
                    if text and text.strip():
                        content_pages.append(text.strip())
                        logger.debug(f"PyMuPDF extracted text from page {page_num + 1}: {len(text)} characters")
                    else:
                        logger.debug(f"PyMuPDF: Page {page_num + 1} contains no extractable text")
                        
                except Exception as page_error:
                    logger.error(f"PyMuPDF error processing page {page_num + 1}: {str(page_error)}")
                    continue
            
            doc.close()
            logger.info(f"PyMuPDF extracted text from {len(content_pages)} out of {total_pages} pages")
            return content_pages
            
        except Exception as e:
            logger.error(f"PyMuPDF error processing {file_path.name}: {str(e)}")
            return []
    
    def _process_pdf_with_pypdf2(self, file_path: Path) -> List[str]:
        """Extract text using PyPDF2 (fallback for text-based PDFs)"""
        content_pages = []
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    logger.warning(f"PyPDF2: PDF file {file_path.name} is encrypted/password-protected")
                    return []
                
                total_pages = len(pdf_reader.pages)
                logger.debug(f"Processing PDF with PyPDF2: {total_pages} pages")
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            content_pages.append(text.strip())
                            logger.debug(f"PyPDF2 extracted text from page {page_num + 1}: {len(text)} characters")
                        else:
                            logger.debug(f"PyPDF2: Page {page_num + 1} contains no extractable text")
                    except Exception as page_error:
                        logger.error(f"PyPDF2 error processing page {page_num + 1}: {str(page_error)}")
                        continue
                
                logger.info(f"PyPDF2 extracted text from {len(content_pages)} out of {total_pages} pages")
                return content_pages
                
        except Exception as e:
            logger.error(f"PyPDF2 error processing {file_path.name}: {str(e)}")
            return []
    
    def _process_pdf_with_ocr(self, file_path: Path) -> List[str]:
        """Extract text using OCR for image-based PDFs"""
        if not OCR_AVAILABLE:
            logger.warning("OCR libraries not available, cannot process image-based PDFs")
            return []
        
        if not self.settings.enable_ocr:
            logger.info("OCR processing is disabled in configuration")
            return []
        
        content_pages = []
        try:
            logger.info(f"Converting PDF to images for OCR processing: {file_path.name}")
            
            # Convert PDF pages to images using configured DPI
            images = convert_from_path(
                str(file_path), 
                dpi=self.settings.ocr_dpi, 
                fmt='jpeg'
            )
            total_pages = len(images)
            
            logger.info(f"OCR processing {total_pages} pages from {file_path.name} "
                       f"(DPI: {self.settings.ocr_dpi}, Language: {self.settings.ocr_language})")
            
            for page_num, image in enumerate(images):
                try:
                    # Perform OCR on the image using configured language
                    text = pytesseract.image_to_string(
                        image, 
                        lang=self.settings.ocr_language
                    )
                    
                    if text and text.strip():
                        content_pages.append(text.strip())
                        logger.debug(f"OCR extracted text from page {page_num + 1}: {len(text)} characters")
                    else:
                        logger.debug(f"OCR: Page {page_num + 1} contains no recognizable text")
                        
                except Exception as page_error:
                    logger.error(f"OCR error processing page {page_num + 1}: {str(page_error)}")
                    continue
            
            logger.info(f"OCR extracted text from {len(content_pages)} out of {total_pages} pages")
            return content_pages
            
        except Exception as e:
            logger.error(f"OCR error processing {file_path.name}: {str(e)}")
            return []
    
    def _process_text(self, file_path: Path) -> List[str]:
        """Process text file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return [content] if content.strip() else []
    
    def _process_docx(self, file_path: Path) -> List[str]:
        """Process DOCX file"""
        doc = docx.Document(file_path)
        content_pages = []
        current_page = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                current_page.append(paragraph.text)
        
        if current_page:
            content_pages.append('\n'.join(current_page))
        
        return content_pages
    
    def _process_excel(self, file_path: Path) -> List[str]:
        """Process Excel file"""
        df = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
        content_pages = []
        
        for sheet_name, sheet_df in df.items():
            # Convert DataFrame to string representation
            sheet_content = f"Sheet: {sheet_name}\n"
            sheet_content += sheet_df.to_string(index=False)
            content_pages.append(sheet_content)
        
        return content_pages
    
    def _process_csv(self, file_path: Path) -> List[str]:
        """Process CSV file"""
        df = pd.read_csv(file_path)
        content = df.to_string(index=False)
        return [content] if content.strip() else []

    def load_document(self, file_path: Path) -> Tuple[bool, List[str], Optional[str]]:
        """
        Load document content using appropriate processor
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Tuple of (success, content_pages, error_message)
        """
        try:
            file_type = self.detect_file_type(file_path.name)
            if not file_type:
                return False, [], f"Unsupported file type: {file_path.suffix}"
            
            # Get appropriate processor
            processor = self.processors.get(file_type)
            if not processor:
                return False, [], f"No processor available for file type: {file_type}"
            
            # Process document
            logger.info(f"Processing document: {file_path.name} as {file_type.value}")
            content_pages = processor(file_path)
            
            logger.info(f"Successfully processed {len(content_pages)} pages from {file_path.name}")
            return True, content_pages, None
            
        except Exception as e:
            logger.error(f"Document processing error for {file_path.name}: {str(e)}")
            return False, [], f"Failed to process document: {str(e)}"
    
    def chunk_document(
        self, 
        content_pages: List[str], 
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[str]:
        """
        Split document content into chunks
        
        Args:
            content_pages: List of page contents
            chunk_size: Custom chunk size (uses default if None)
            chunk_overlap: Custom overlap size (uses default if None)
            
        Returns:
            List of text chunks
        """
        try:
            # Use custom or default chunk settings
            chunk_size = chunk_size or self.settings.chunk_size
            chunk_overlap = chunk_overlap or self.settings.chunk_overlap
            
            # Combine all pages
            full_text = "\n\n".join(content_pages).strip()
            
            # Check if we have any text to chunk
            if not full_text:
                logger.warning("No text content found after combining pages")
                return []
            
            logger.info(f"Total text length: {len(full_text)} characters")
            
            # Simple text chunking implementation
            chunks = []
            start = 0
            
            while start < len(full_text):
                end = start + chunk_size
                
                # If we're not at the end, try to break at a sentence or word boundary
                if end < len(full_text):
                    # Look for sentence boundary (. followed by space or newline)
                    sentence_end = full_text.rfind('. ', start, end)
                    if sentence_end > start:
                        end = sentence_end + 1
                    else:
                        # Look for word boundary
                        word_end = full_text.rfind(' ', start, end)
                        if word_end > start:
                            end = word_end
                
                chunk = full_text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                
                # Move start position with overlap
                start = max(start + 1, end - chunk_overlap)
            
            logger.info(f"Created {len(chunks)} chunks with size {chunk_size} and overlap {chunk_overlap}")
            return chunks
            
        except Exception as e:
            logger.error(f"Document chunking error: {str(e)}")
            return []
    
    def create_chunk_metadata(
        self,
        chunks: List[str],
        filename: str,
        file_type: FileType,
        access_level: AccessLevel,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> List[ChunkMetadata]:
        """
        Create metadata for document chunks
        
        Args:
            chunks: List of text chunks
            filename: Source filename
            file_type: Type of source file
            access_level: Access level for chunks
            custom_metadata: Additional custom metadata
            
        Returns:
            List of chunk metadata objects
        """
        chunk_metadatas = []
        current_char = 0
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{Path(filename).stem}_{i}_{uuid.uuid4().hex[:8]}"
            
            start_char = current_char
            end_char = current_char + len(chunk)
            current_char = end_char
            
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                filename=filename,
                file_type=file_type,
                access_level=access_level,
                chunk_index=i,
                chunk_size=len(chunk),
                start_char=start_char,
                end_char=end_char,
                created_at=datetime.now()
            )
            
            chunk_metadatas.append(metadata)
        
        return chunk_metadatas
    
    def process_document(
        self,
        filename: str,
        access_level: AccessLevel = AccessLevel.USER,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete document processing pipeline
        
        Args:
            filename: Name of uploaded file
            access_level: Access level for the document
            chunk_size: Custom chunk size
            chunk_overlap: Custom overlap size
            custom_metadata: Additional metadata
            
        Returns:
            Processing result dictionary
        """
        start_time = time.time()
        
        try:
            file_path = self.upload_dir / filename
            
            # Validate file
            is_valid, error_msg = self.validate_file(file_path)
            if not is_valid:
                return {
                    "success": False,
                    "error": error_msg,
                    "filename": filename
                }
            
            # Detect file type
            file_type = self.detect_file_type(filename)
            if not file_type:
                return {
                    "success": False,
                    "error": f"Unsupported file type: {Path(filename).suffix}",
                    "filename": filename
                }
            
            # Load document
            success, content_pages, load_error = self.load_document(file_path)
            if not success:
                return {
                    "success": False,
                    "error": load_error,
                    "filename": filename
                }
            
            # Check if we have content to chunk
            if not content_pages:
                if OCR_AVAILABLE:
                    error_msg = (f"No text content could be extracted from {filename}. "
                               f"This file may be corrupted, password-protected, contain only blank pages, "
                               f"or have text that is not recognizable by OCR. "
                               f"Please verify the file is valid and contains readable content.")
                else:
                    error_msg = (f"No text content could be extracted from {filename}. "
                               f"This PDF appears to contain only images or scanned content, but OCR libraries "
                               f"are not available. Please install OCR dependencies (pytesseract, pdf2image, pymupdf) "
                               f"or upload a text-based PDF.")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "filename": filename
                }
            
            # Chunk document
            chunks = self.chunk_document(content_pages, chunk_size, chunk_overlap)
            if not chunks:
                return {
                    "success": False,
                    "error": f"Unable to create text chunks from {filename}. The extracted content is too short, contains only whitespace, or formatting characters. Please ensure the document contains readable text content.",
                    "filename": filename
                }
            
            # Create chunk metadata
            chunk_metadatas = self.create_chunk_metadata(
                chunks, filename, file_type, access_level, custom_metadata
            )
            
            # Prepare data for vector database
            chunk_ids = [metadata.chunk_id for metadata in chunk_metadatas]
            metadata_dicts = []
            
            for metadata in chunk_metadatas:
                metadata_dict = {
                    "chunk_id": metadata.chunk_id,
                    "filename": metadata.filename,
                    "file_type": metadata.file_type.value,
                    "access_level": metadata.access_level.value,
                    "chunk_index": metadata.chunk_index,
                    "chunk_size": metadata.chunk_size,
                    "start_char": metadata.start_char,
                    "end_char": metadata.end_char,
                    "created_at": metadata.created_at.isoformat()
                }
                
                # Add custom metadata if provided
                if custom_metadata:
                    metadata_dict.update(custom_metadata)
                
                metadata_dicts.append(metadata_dict)
            
            # Add chunks to vector database
            success = self.vector_db.add_chunks(chunk_ids, chunks, metadata_dicts)
            if not success:
                return {
                    "success": False,
                    "error": "Failed to add chunks to vector database",
                    "filename": filename
                }
            
            # Create document metadata
            file_size = file_path.stat().st_size
            doc_metadata = DocumentMetadata(
                filename=filename,
                file_type=file_type,
                access_level=access_level,
                file_size=file_size,
                uploaded_at=datetime.now(),
                total_chunks=len(chunks),
                chunk_size=chunk_size or self.settings.chunk_size,
                chunk_overlap=chunk_overlap or self.settings.chunk_overlap,
                custom_metadata=custom_metadata
            )
            
            processing_time = time.time() - start_time
            
            logger.info(f"Successfully processed {filename}: {len(chunks)} chunks in {processing_time:.2f}s")
            
            return {
                "success": True,
                "filename": filename,
                "chunks_created": len(chunks),
                "document_metadata": doc_metadata,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Document processing error for {filename}: {str(e)}")
            return {
                "success": False,
                "error": f"Document processing failed: {str(e)}",
                "filename": filename
            }


# Global processor instance
_processor_instance: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """
    Get document processor instance (singleton)
    
    Returns:
        DocumentProcessor instance
    """
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = DocumentProcessor()
        logger.info("Document processor initialized")
        
        # Log OCR availability
        if OCR_AVAILABLE:
            logger.info("OCR capabilities available - can process image-based PDFs")
        else:
            logger.warning("OCR capabilities not available - only text-based PDFs will be processed")
    return _processor_instance