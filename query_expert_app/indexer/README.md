# Document Indexer Service

A FastAPI-based document indexing service that uses OpenSearch for vector storage and Ollama with Gemma embeddings for semantic search.

## Features

- **Document Processing**: Support for PDF, TXT, DOCX, XLSX, CSV, and MD files
- **Vector Search**: OpenSearch with KNN vector search capabilities
- **Embeddings**: Ollama with Gemma:latest model for generating embeddings
- **Access Control**: Role-based access control for documents
- **Chunking**: Intelligent text chunking with configurable size and overlap
- **REST API**: FastAPI-based REST endpoints for document management

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   OpenSearch    │    │     Ollama      │
│                 │    │                 │    │                 │
│ - Upload docs   │◄──►│ - Vector store  │    │ - Gemma model   │
│ - Search docs   │    │ - KNN search    │◄──►│ - Embeddings    │
│ - Manage docs   │    │ - Metadata      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Prerequisites

### 1. OpenSearch
Install and run OpenSearch locally:

**Using Docker:**
```bash
docker run -d \
  --name opensearch \
  -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "plugins.security.disabled=true" \
  -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=admin123" \
  opensearchproject/opensearch:latest
```

**Or download and install:**
1. Download OpenSearch from https://opensearch.org/downloads.html
2. Extract and run: `./bin/opensearch`
3. Verify: `curl http://localhost:9200`

### 2. Ollama with Nomic Embed Text
Install Ollama and pull the Nomic embedding model:

```bash
# Install Ollama (visit https://ollama.ai for installation instructions)
# Then pull the Nomic embedding model
ollama pull nomic-embed-text:v1.5

# Start Ollama service (usually runs automatically)
ollama serve
```

Verify Ollama is running: `curl http://localhost:11434/api/tags`

## Installation

1. **Clone and navigate to the project:**
```bash
cd query_expert_app/indexer
```

2. **Install dependencies using Poetry:**
```bash
poetry install
```

3. **Create environment file:**
```bash
cp .env.example .env
```

4. **Configure settings in `.env`:**
```env
# OpenSearch settings
OPENSEARCH_URL=http://localhost:9200
OPENSEARCH_INDEX=documents

# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text:v1.5

# Document processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_FILE_SIZE_MB=50
```

## Usage

```

### 1. Start the Service
```bash
poetry run python main.py
```

The service will be available at `http://localhost:8002`

### 3. API Documentation
Visit `http://localhost:8002/docs` for interactive API documentation.

## API Endpoints

### Document Management
- `POST /indexing/upload` - Upload and index a document
- `DELETE /management/documents/{filename}` - Delete a document
- `GET /management/files` - List all indexed files
- `GET /management/stats` - Get collection statistics

### Search
- `POST /search/query` - Search documents with semantic similarity
- `GET /search/chunk/{chunk_id}` - Get specific chunk by ID

### Example Usage

**Upload a document:**
```bash
curl -X POST "http://localhost:8002/indexing/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "access_level=user"
```

**Search documents:**
```bash
curl -X POST "http://localhost:8002/search/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "access_level": "user",
    "max_results": 5
  }'
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENSEARCH_URL` | `http://localhost:9200` | OpenSearch connection URL |
| `OPENSEARCH_INDEX` | `documents` | Index name for documents |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service URL |
| `OLLAMA_MODEL` | `gemma:latest` | Ollama model for embeddings |
| `CHUNK_SIZE` | `1000` | Text chunk size in characters |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `MAX_FILE_SIZE_MB` | `50` | Maximum file size for upload |

### Access Levels
- `administrator` - Full access to all documents
- `user` - Access to user and guest level documents
- `guest` - Access to guest level documents only

## Development

### Project Structure
```
indexer/
├── src/
│   ├── core/           # Core functionality
│   │   ├── config.py   # Configuration management
│   │   └── vector_db.py # OpenSearch integration
│   ├── models/         # Pydantic models
│   ├── routers/        # FastAPI routers
│   ├── services/       # Business logic
│   └── utils/          # Utility functions
├── tests/              # Test files
├── uploads/            # Uploaded files storage
└── main.py            # Application entry point
```

### Running Tests
```bash
poetry run pytest
```

### Code Quality
```bash
# Format code
poetry run black .

# Lint code
poetry run flake8 .
```

## Troubleshooting

### Common Issues

1. **OpenSearch connection refused**
   - Ensure OpenSearch is running on port 9200
   - Check firewall settings
   - Verify OpenSearch configuration

2. **Ollama model not found**
   - Pull the model: `ollama pull nomic-embed-text:v1.5`
   - Verify Ollama is running: `ollama list`

3. **Large file upload fails**
   - Check `MAX_FILE_SIZE_MB` setting
   - Ensure sufficient disk space

4. **Embedding generation slow**
   - Consider using a smaller model
   - Check system resources (CPU/Memory)

### Logs
Check application logs for detailed error information:
```bash
poetry run python main.py --log-level DEBUG
```

## Performance Considerations

- **Embedding Generation**: Nomic embedding model requires significant CPU/GPU resources
- **Index Size**: Large document collections may require OpenSearch tuning
- **Memory Usage**: Adjust chunk size based on available memory
- **Concurrent Uploads**: Limit concurrent file processing to prevent resource exhaustion

## Security

- **Access Control**: Implement proper authentication before production use
- **File Validation**: Only allow trusted file types and sources
- **Network Security**: Use HTTPS and secure OpenSearch deployment
- **Data Privacy**: Consider encryption for sensitive documents

## License

This project is part of the Query Expert App system.