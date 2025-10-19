# SQL Agent - GenAI Chatbot Application

## Overview
This is a full-stack application that provides a conversational AI interface for querying SQL databases. It consists of:
- **Angular Frontend**: Modern chatbot UI with real-time polling
- **FastAPI Backend**: Main API and Data API for database access
- **Celery Worker**: Background task processor using LangChain and Ollama
- **Redis**: Message broker for Celery tasks
- **SQLite**: Data storage

## Architecture

### Components
1. **Frontend** (Port 5000) - Angular 18 application
   - Location: `frontend/`
   - Chatbot UI with message history
   - Real-time polling for task status
   - Proxy configuration to backend API

2. **Main API** (Port 8000) - FastAPI
   - Location: `query_expert_app/api/`
   - Endpoints: `/api/ask`, `/api/task/{task_id}`
   - Submits tasks to Celery worker via Redis

3. **Data API** (Port 8001) - FastAPI
   - Location: `query_expert_app/data_api/`
   - Provides read-only SQL query execution
   - Database schema inspection

4. **Worker** - Celery
   - Location: `query_expert_app/worker/`
   - Processes user questions using LangChain
   - Executes SQL queries via Data API

### Technology Stack
- **Frontend**: Angular 18, TypeScript, RxJS
- **Backend**: Python 3.12, FastAPI, Poetry
- **Worker**: Celery, LangChain, Ollama (LLM)
- **Database**: SQLite
- **Message Broker**: Redis

## Recent Changes
- **2025-10-19**: Initial setup and configuration for Replit environment
  - Installed Python 3.12 and Node.js 20
  - Installed all Python dependencies using Poetry
  - Created Angular frontend with chatbot UI
  - Configured proxy for API communication
  - Created startup script to run all services
  - Created sample SQLite database for testing

## Project Structure
```
.
├── frontend/                 # Angular frontend application
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/chat/  # Chatbot component
│   │   │   ├── services/         # HTTP services
│   │   │   └── ...
│   ├── proxy.conf.json      # API proxy configuration
│   └── angular.json         # Angular configuration
├── query_expert_app/        # Python backend
│   ├── api/                 # Main API
│   ├── data_api/            # Database API
│   ├── worker/              # Celery worker
│   └── common/              # Shared configuration
├── data/                    # Database files
│   └── database.db         # SQLite database
├── start.sh                # Startup script for all services
└── replit.md               # This file
```

## API Endpoints

### Main API (Port 8000)
- `POST /api/ask` - Submit a question
  - Request: `{ "question": "your question here" }`
  - Response: `{ "task_id": "...", "status": "INPROGRESS", "message": "..." }`

- `GET /api/task/{task_id}` - Get task status
  - Response: `{ "task_id": "...", "status": "SUCCESS|INPROGRESS|FAILURE", "progress_message": "...", "result": "...", "error": null }`

### Data API (Port 8001)
- `GET /api/schema/` - Get database schema
- `POST /api/query/execute` - Execute SQL query
- `GET /api/table/{table_name}` - Get table data

## Running the Application

The application starts all services automatically through the configured workflow:
1. Redis server
2. Data API (port 8001)
3. Celery Worker
4. Main API (port 8000)
5. Angular Frontend (port 5000)

All services run in the background, and the frontend is accessible on port 5000.

## Configuration

### Backend Configuration
Configuration is managed through JSON files in `query_expert_app/common/config/`:
- `common.config.json` - Application-wide settings
- `worker.config.json` - Celery worker settings

### Frontend Configuration
- `angular.json` - Build and serve configuration
- `proxy.conf.json` - API proxy settings

## Development Notes

### Angular Polling Pattern
The frontend uses RxJS operators to poll the task status endpoint:
- `timer(0, 5000)` - Poll every 5 seconds
- `switchMap` - Switch to new request on each interval
- `takeWhile` - Stop polling when status is not INPROGRESS
- `timeout(300000)` - 5-minute timeout

### Backend Task Flow
1. User submits question via `/api/ask`
2. API creates Celery task and returns task_id
3. Frontend polls `/api/task/{task_id}` every 5 seconds
4. Worker processes task using LangChain agent
5. Worker updates task status in Redis
6. Frontend receives final result when status changes to SUCCESS/FAILURE

## User Preferences
- None specified yet

## Dependencies

### Python Dependencies (Poetry)
See individual `pyproject.toml` files in:
- `query_expert_app/api/pyproject.toml`
- `query_expert_app/data_api/pyproject.toml`
- `query_expert_app/worker/pyproject.toml`

### Node.js Dependencies
See `frontend/package.json`

## Troubleshooting

### If services don't start
1. Check that Redis is running: `redis-cli ping`
2. Check Python dependencies are installed in each component
3. Check Angular dependencies: `cd frontend && npm install`

### If frontend can't connect to backend
1. Verify proxy configuration in `frontend/proxy.conf.json`
2. Check that API is running on port 8000
3. Check browser console for CORS errors

### If worker doesn't process tasks
1. Check Redis connection
2. Verify Ollama is available (if using LLM features)
3. Check worker logs for errors
