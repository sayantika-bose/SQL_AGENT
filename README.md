
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
- **Worker**: Celery, LangChain, LangGraph, Ollama (LLM)
- **Database**: SQLite
- **Message Broker**: Redis

## Running the Application (Local Setup with Poetry)

### Prerequisites
- Python 3.12+
- Node.js 20+
- Poetry
- Redis (running in Docker or locally)
- Ollama (optional, for LLM features)

### Steps

#### 1. Run Redis
Ensure Redis is running before starting any backend service:
```bash
docker run -d -p 6379:6379 redis
```

#### 2. Run the Data API
Before running Data API, make sure the database file is in place:
```
query_expert_app/data_api/src/db/financial_data.db
```

Then open a terminal in the `query_expert_app/data_api/` directory and run:
```bash
poetry lock
poetry install
$env:PYTHONPATH="Your_Path\SQL_AGENT\query_expert_app"
poetry run python main.py
```

#### 3. Run the Main API
Open a terminal in the `query_expert_app/api/` directory and run:
```bash
poetry lock
poetry install
$env:PYTHONPATH="Your_Path\SQL_AGENT\query_expert_app"
poetry run python main.py
```

#### 4. Run the Celery Worker
Open a terminal in the `query_expert_app/worker/` directory and run:
```bash
poetry lock
poetry install
$env:PYTHONPATH="Your_Path\SQL_AGENT\query_expert_app"
poetry run celery -A worker.tasks worker --loglevel=info
```

#### 5. Run the Angular Frontend
In the `frontend/` directory, execute:
```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
npm install
npm start
```
Make sure Node.js is installed and accessible in PATH.

The frontend will be available at **http://localhost:5000**.

## Database Schema

The application uses a relational **SQLite** database located at `query_expert_app/data_api/src/db/financial_data.db`.

### Tables Overview
The database contains several related tables that store financial and transactional information:
- **Users** – Stores user information such as `user_id`, `name`, and `email`.
- **Orders** – Stores purchase order details, each linked to a user via `user_id`.
- **Products** – Contains product details including `product_id`, `name`, and `price`.
- **FinancialTransactions** – Records transaction data, linking users and orders.

### Relationships
- **Users ↔ Orders**: One-to-Many (one user can have multiple orders)
- **Orders ↔ FinancialTransactions**: One-to-Many (one order can have multiple transactions)
- **Products ↔ Orders**: Many-to-Many through an intermediate join table (if implemented)

This relational design ensures data normalization, reducing redundancy and improving query performance for analytics and reporting.

## Design Choices

### Architecture
The project follows a **task-based architecture** using **Celery workers** for asynchronous processing. This allows heavy LLM inference and SQL query analysis tasks to run in the background without blocking API responses.

Key reasons for this architecture:
- **Scalability**: Celery enables distributed task processing, allowing horizontal scaling by adding more workers.
- **Responsiveness**: The FastAPI service remains lightweight and responsive since long-running tasks are offloaded to the worker.
- **Reliability**: Redis acts as the message broker, ensuring task persistence and fault tolerance.

### Model and Prompting Strategy
The **LangChain + Ollama** stack is used for natural language query interpretation. The LLM is prompted with structured context about the database schema to generate accurate SQL queries from user questions.

Prompt structure example:
```
You are an expert SQL assistant. Given the database schema and user question, generate the correct SQL query.
Schema: {schema_description}
Question: {user_input}
```
This guided prompting ensures the model generates contextually relevant SQL commands.

### Why This Design
- The modular separation between APIs, worker, and frontend ensures clean architecture.
- Using **Poetry** provides isolated environments for each backend service, simplifying dependency management.
- The **frontend polling pattern** (using RxJS) efficiently checks task status without WebSocket overhead.

## Limitations
- Currently limited to SQLite; scaling to PostgreSQL or MySQL may require schema migration.
- Ollama model performance depends on system resources (RAM/VRAM).
- No authentication layer yet for API endpoints (planned enhancement).
