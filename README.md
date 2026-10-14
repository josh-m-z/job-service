# Job Service

A backend service for **asynchronous job execution and PDF document processing**, built with Python, FastAPI, PostgreSQL, Redis, and Celery.

The project focuses on reliable background processing, including handling failed jobs, worker interruptions, and duplicate requests. It also supports individual and batch PDF uploads, text extraction, and basic document analysis.

## Tech Stack

- **Backend:** Python, FastAPI, Pydantic
- **Database:** PostgreSQL, psycopg
- **Background Processing:** Celery, Redis
- **Document Processing:** pypdf, regular expressions
- **Development:** Docker Compose

## Features

- **Asynchronous Jobs:** Submit jobs through REST APIs for background execution.
- **Persistent Job Tracking:** Store job statuses, results, errors, and execution attempts in PostgreSQL.
- **Retries and Recovery:** Retry failed jobs and track interrupted execution attempts.
- **Idempotency:** Detect duplicate job submissions using idempotency keys.
- **Transactional Outbox:** Persist jobs and dispatch events in the same database transaction to reduce the risk of losing accepted work.
- **PDF Processing:** Extract text, page counts, word counts, and structured information from documents.
- **Batch Processing:** Upload multiple PDFs and track individual and overall processing progress.

## Architecture

The application separates API request handling from background execution.

```text
Client
  |
  v
FastAPI
  |
  v
PostgreSQL (Jobs + Outbox Events)
  |
  v
Outbox Dispatcher
  |
  v
Redis (Message Broker)
  |
  v
Celery Worker
  |
  v
PostgreSQL (Results + Execution History)
```

**Execution flow:**

1. A client submits a job or uploads a PDF through FastAPI.
2. The API validates the request and stores the job alongside an outbox event in PostgreSQL.
3. The dispatcher publishes pending tasks to Celery through Redis.
4. A worker executes the job and records its result or failure.
5. Failed jobs can be retried, while clients can retrieve processing statuses and results through the API.

PostgreSQL maintains persistent job state, while Redis handles task messaging.

## Document Processing

The application supports individual PDF uploads and batches of documents.

For each PDF, it extracts:

- Full text, page count, word count, and character count
- Basic document classification, including invoices, resumes, and receipts
- Titles, dates, monetary amounts, and organization names using keyword and pattern matching

Extracted document data is stored separately from job execution records, allowing results to be retrieved independently.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/jobs` | Submit a background job |
| GET | `/jobs` | List all jobs |
| GET | `/jobs/{job_id}` | Retrieve a job |
| GET | `/jobs/{job_id}/cancel` | Cancel a queued job |
| POST | `/documents` | Upload a PDF |
| GET | `/documents/{document_id}/result` | Retrieve extracted document data |
| POST | `/batches` | Upload multiple PDFs |
| GET | `/batches/{batch_id}` | Retrieve batch status and results |

Interactive API documentation is available at `http://localhost:8000/docs`.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/josh-m-z/job-service.git
cd job-service
```

### 2. Install Dependencies

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### 3. Start PostgreSQL and Redis

```bash
docker compose up -d
```

### 4. Configure the Database

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://jobuser:jobpassword@localhost:5432/jobservice
```

The database schema is initialized automatically when FastAPI starts.

### 5. Start the Application

Run each component in a separate terminal, with the virtual environment activated.

**FastAPI server:**

```bash
uvicorn backend.main:app --reload
```

**Celery worker:**

```bash
celery -A backend.celery_app.celery_app worker --loglevel=info
```

**Outbox dispatcher:**

```bash
python -m backend.dispatcher
```

The API is available at `http://localhost:8000`.

## Example Usage

Submit a job to calculate the sum of a list of numbers:

**POST** `/jobs`

```json
{
  "job_type": "sum_numbers",
  "payload": {
    "numbers": [10, 20, 30]
  },
  "idempotency_key": "example-001"
}
```

The API creates a persistent job that is processed asynchronously. Its status can be retrieved through `GET /jobs/{job_id}`.

PDFs can also be uploaded through `/documents` or `/batches` using multipart form data.

## Project Status

This project is under active development. Current work focuses on improving reliability, validating end-to-end execution, and expanding document processing capabilities.
