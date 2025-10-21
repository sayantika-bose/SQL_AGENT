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
The database contains several related tables that store financial, operational, and port activity data:

1. **Volumes** – Stores port volume data with commodity and entity information
   - Columns: `Port`, `State`, `Commodity`, `Entity`, `Type`, `Period`, `Value`
   
2. **BalanceSheet** – Contains hierarchical financial balance sheet data
   - Columns: `Line Item`, `Category`, `SubCategory`, `SubSubCategory`, `Period`, `Value`
   
3. **CashFlowStatement** – Records cash flow items by category and period
   - Columns: `Item`, `Category`, `Period`, `Value`
   - Foreign Keys: References `BalanceSheet` (`Category`, `Period`)
   
4. **Consolidated_PnL** – Stores consolidated profit and loss statement data
   - Columns: `Line Item`, `Period`, `Value`
   - Foreign Keys: References `BalanceSheet` (`Line Item`, `Period`)
   
5. **Quarterly_PnL** – Contains quarterly profit and loss data with period types
   - Columns: `Item`, `Category`, `Period`, `Value`, `Period Type`
   - Foreign Keys: References `BalanceSheet` (`Category`, `Period`)
   
6. **Containers** – Records container-related metrics by port and entity
   - Columns: `Port`, `Entity`, `Type`, `Period`, `Value`
   - Foreign Keys: References `Volumes` (`Port`, `Period`)
   
7. **ROCE_External** – Stores external Return on Capital Employed metrics
   - Columns: `Particular`, `Period`, `Value`
   - Foreign Keys: References `BalanceSheet` (`Period`)
   
8. **ROCE_Internal** – Contains internal ROCE data categorized by port and line item
   - Columns: `Category`, `Port`, `Line Item`, `Period`, `Value`
   - Foreign Keys: References `BalanceSheet` (`Category`, `Line Item`, `Period`) and `Volumes` (`Port`)
   
9. **RORO** – Records Roll-on/Roll-off vessel operations and vehicle counts
   - Columns: `Port`, `Type`, `Period`, `Value`, `Number of Cars`
   - Foreign Keys: References `Volumes` (`Port`, `Period`)

### Relationships
- **BalanceSheet** acts as a central reference table for financial data:
  - Referenced by `CashFlowStatement` (Category, Period)
  - Referenced by `Consolidated_PnL` (Line Item, Period)
  - Referenced by `Quarterly_PnL` (Category, Period)
  - Referenced by `ROCE_External` (Period)
  - Referenced by `ROCE_Internal` (Category, Line Item, Period)

- **Volumes** serves as a reference for operational port data:
  - Referenced by `Containers` (Port, Period)
  - Referenced by `ROCE_Internal` (Port)
  - Referenced by `RORO` (Port, Period)

### Database Creation
The database is populated from CSV files using the import script. Each table corresponds to a CSV file with matching column names. The script:
1. Creates tables with appropriate schema and foreign key constraints
2. Imports data from CSV files located in the configured CSV folder path
3. Maintains referential integrity through foreign key relationships

### Configuration
Database and CSV paths are configured via environment variables:
- `DATABASE_PATH` – Path to the SQLite database file
- `CSV_FOLDER_PATH` – Directory containing the source CSV files

This relational design ensures data normalization and maintains consistency across financial statements, operational metrics, and port activity data, enabling complex analytical queries and reporting.

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
