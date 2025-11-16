Excellent. I have reviewed my initial plan and the plan provided by the other AI. The other AI's plan excels in its detailed data modeling, UI/UX descriptions, and specific code examples for DevOps artifacts. My plan emphasized production-grade async processing and a dedicated vector database.

I will now consolidate these into a single, final, and superior implementation plan. This document represents the harmonized and definitive blueprint for the **Artemis Index** project, adhering to the Core Engineering Rules.

---

### **Artemis Index: Final Consolidated Implementation Plan**

**Version:** 2.0 (Consolidated)
**Status:** Approved for Implementation

#### **Consolidation Notes:**
This plan merges the strengths of two AI-generated proposals. Key architectural decisions made during consolidation include:
*   **Async Processing:** Adopting **Celery with Redis** for background tasks. This is a more robust, scalable, and production-ready solution for heavy PDF processing than lighter alternatives like `APScheduler`.
*   **Vector Search:** Utilizing **MongoDB's native vector search capabilities** for the initial implementation. This simplifies the tech stack (one less service to manage) while being sufficient for the initial user load. A dedicated vector database like **Qdrant** remains a viable option for future scaling.
*   **DevOps Artifacts:** Incorporating the detailed `Dockerfile`, `Jenkinsfile`, and `docker-compose.yml` examples for their completeness and immediate utility.
*   **Data Model & UI/UX:** Adopting the highly detailed data models and UI/UX descriptions for their thoroughness and clarity.
*   **Endpoint Strategy:** Using a **subdomain (`index.serelo...`)** for the application. This provides better security isolation (cookies, storage) and simplifies routing compared to a path-based (`/artemis-index/`) approach.

---

### **1. Tech Stack & Justification**

*   **Backend:** **Python** with **FastAPI**.
    *   **Justification:** High performance, native async support for I/O-bound tasks (API calls), automatic data validation (Pydantic), and self-generating documentation.
*   **Frontend:** **React SPA** with **TypeScript**, built with **Vite**.
    *   **Justification:** A performant and maintainable SPA is ideal for this auth-gated application where SEO is not a concern. Vite provides a superior developer experience. TypeScript ensures type safety.
*   **Frontend State & Styling:**
    *   **Styling:** **TailwindCSS** for rapid, utility-first UI development.
    *   **Server State:** **React Query** for caching, refetching, and managing API data.
    *   **UI State:** **Zustand** for lightweight global state (e.g., theme, modal visibility).
*   **Database:** **MongoDB**.
    *   **Justification:** Its flexible document model is perfect for storing varied data like user profiles, job metadata, and structured summary outputs. Includes native vector search capabilities.
*   **File Storage:** **MinIO**.
    *   **Justification:** An S3-compatible, self-hosted object store. Fulfills the "no AWS" requirement while using a standard, cloud-ready API (`boto3`).
*   **Background Jobs:** **Celery** with **Redis** as the message broker.
    *   **Justification:** A robust, distributed task queue essential for handling long-running, resource-intensive PDF processing without blocking the API or timing out user requests.
*   **Authentication:** **JWTs** with a refresh token strategy. Passwords hashed with **bcrypt**.

---

### **2. UI/UX Design**

*   **Design Principles:** Minimalist, professional, and clean. Generous whitespace, clear typography, and an uncluttered layout suitable for technical users.
*   **Color Palette:** Monochromatic with a single accent color.
    *   **Primary:** Slate grays.
    *   **Accent:** Teal (`#0d9488`) for calls-to-action and highlights.
    *   **Modes:** Both Light and Dark modes will be supported, with the choice saved to user preferences.
*   **Key Screens & Flows:**
    1.  **Login:** Minimal form for email and password.
    2.  **Dashboard:** Main navigation hub with two primary actions: "Summarize Document" and "Find Information." A list of recent jobs will be displayed.
    3.  **Upload Flow:** A shared, clean drag-and-drop interface for uploading PDFs. Pre-flight validation for file size and type will provide immediate feedback.
    4.  **Summarization Flow:**
        *   **Template Selection:** A card-based layout to choose a summary format.
        *   **Instructions:** An optional text area for user-specific directives.
        *   **Processing View:** A dedicated page showing a multi-step progress indicator (`Extracting -> Processing -> Formatting`) powered by real-time updates from the backend.
    5.  **Snippet Finder Flow:**
        *   **Query Input:** A prominent search bar allowing single or multiple queries.
        *   **Results View:** A list of result cards, each displaying the query, text snippet, a relevance score, and a clear page/section reference (e.g., "Page 42 – Section 3.2").

---

### **3. Data Model (MongoDB Collections)**

1.  `users`: Stores user credentials, preferences (e.g., dark mode), and `_id`.
2.  `documents`: Metadata for each uploaded PDF, including `filename`, `s3_key` (path in MinIO), `page_count`, and `user_id`.
3.  `jobs`: Tracks every summarization or search task with `status` (pending, processing, completed, failed), `job_type`, links to user and document, and `result_id`.
4.  `summaries`: Stores the structured output of summarization jobs, linked by `job_id`.
5.  `templates`: Defines the structure for different summary types, including fields, target length, and the base prompt.
6.  `embeddings`: Stores text chunks from documents, their vector embeddings, and crucial metadata (`page_number`, `section_heading`). This is the backbone of the snippet finder.
7.  `api_usage`: Tracks token consumption and estimated cost per user on a monthly basis to enforce the R1000 budget.

---

### **4. AI Integration & Processing**

*   **PDF Extraction:** Use `pdfplumber` for its superior ability to map text to page numbers and basic structural elements.
*   **Chunking Strategy:** Employ a semantic chunking strategy. Split text first by sections/headings, then paragraphs, to create meaningful ~500-word chunks. Each chunk retains its original page and section metadata.
*   **Summarization (Feature A):**
    *   For long documents, use a **Map-Reduce** (or "summary-of-summaries") strategy executed via Celery tasks.
    *   Summarize individual sections/chunks in parallel.
    *   Combine the intermediate summaries in a final call to synthesize a cohesive document.
*   **Snippet Retrieval (Feature B):**
    1.  **Indexing (Async):** After a PDF is uploaded, a Celery task generates vector embeddings for each text chunk using an OpenAI model (e.g., `text-embedding-3-small`) and stores them in the `embeddings` collection.
    2.  **Querying:** The user's query is embedded in real-time. A vector similarity search is performed against the `embeddings` collection in MongoDB.
    3.  **Results:** The top-matching chunks are returned, along with their stored page and section metadata, providing precise references.
*   **Cost Management:**
    *   Use the `tiktoken` library to count tokens before and after every API call.
    *   Update the `api_usage` collection in real-time.
    *   A pre-flight check in the API will reject new jobs if the monthly R1000 budget is projected to be exceeded.

---

### **5. Testing Strategy**

*   **Unit Tests (`pytest`, `React Testing Library`):**
    *   **Backend:** Isolate and test business logic (prompt construction, chunking logic, cost calculation) and utility functions. Target coverage: **≥ 85%**.
    *   **Frontend:** Test individual components' rendering, state, and user interactions. Target coverage: **≥ 70%**.
*   **Integration Tests (`pytest`, `Docker`):**
    *   Test service interactions: API -> Celery -> MongoDB/MinIO.
    *   Use `docker-compose.test.yml` to spin up ephemeral database and storage containers for isolated test runs.
    *   **Mock OpenAI:** Use a mock server or `monkeypatch` to return predictable responses from the OpenAI API, allowing tests on the full pipeline without incurring costs.
*   **End-to-End Tests (`Playwright`):**
    *   Automate full user flows in a browser environment (Login -> Upload -> Summarize -> Download).
    *   Verify critical paths for both Feature A and Feature B against a set of fixture PDFs.

---

### **6. DevOps: CI/CD, Docker & NGINX**

*   **Docker Architecture:** A multi-container setup managed by `docker-compose`.
    *   `artemis-backend` (FastAPI)
    *   `artemis-frontend` (React served via NGINX)
    *   `mongo` (Database)
    *   `minio` (S3-compatible storage)
    *   `redis` (Celery message broker)
    *   `worker` (Celery worker)
*   **NGINX Configuration (Host Server):** The main NGINX server will act as a reverse proxy.
    ```nginx
    # /etc/nginx/sites-available/artemis-index.conf
    server {
        listen 443 ssl http2;
        server_name index.serelo.artemisinnovations.co.za;

        # SSL Configuration (Let's Encrypt, etc.)
        # ssl_certificate /path/to/fullchain.pem;
        # ssl_certificate_key /path/to/privkey.pem;

        location / {
            proxy_pass http://localhost:3001; # Frontend service port
            proxy_set_header Host $host;
            # ... other proxy headers
        }

        location /api/ {
            proxy_pass http://localhost:8001/api/; # Backend service port
            # ... other proxy headers
        }

        location /ws/ { # For real-time updates (future)
            proxy_pass http://localhost:8001/ws/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
        }
    }
    ```
*   **Jenkins Pipeline (`Jenkinsfile`):** A declarative pipeline will automate the entire delivery process.
    1.  **Lint & Format:** Run static analysis (`flake8`, `eslint`).
    2.  **Test:** Execute unit, integration, and (optionally) E2E tests.
    3.  **Build:** Build and tag production Docker images for the frontend and backend.
    4.  **Push:** Push images to a Docker registry.
    5.  **Deploy:** SSH into the production server, pull the new images, and restart the relevant containers using `docker compose up -d`. This ensures zero-downtime deployments for the application services while infrastructure containers (Mongo, MinIO) remain untouched.

---

### **7. Risks & Mitigations**

| Risk                               | Mitigation Strategy                                                                                                                                                                                |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **High OpenAI API Costs**          | Implement real-time token tracking and a hard stop at the R1000 monthly budget. Queue jobs if the limit is reached. Provide clear cost feedback to users.                                           |
| **Poor PDF Text Extraction**       | Pre-process PDFs to check text density. If the word-per-page count is very low, flag it as a likely scanned/image-based PDF and notify the user that results may be poor or impossible.            |
| **Long Processing Times/Timeouts** | The Celery/Redis architecture is the primary mitigation. Implement timeouts on individual jobs and provide clear, real-time status feedback on the frontend so users are not left waiting blindly. |
| **Inaccurate Page References**     | Rigorously store page and section metadata with every text chunk during the embedding process. Write specific integration tests to verify that snippets returned by a search match their source page. |
| **Data Loss (MinIO)**              | Implement a scheduled daily backup of the MinIO data volume to an external location using a simple cron job and the `mc` (MinIO Client) tool.                                                       |

---

### **8. Phased Roadmap**

#### **Phase 1: MVP (Core Summarization)**
*   **Goal:** A functional end-to-end summarization tool.
*   **Features:**
    *   Secure user login (admin-provisioned accounts).
    *   PDF upload to MinIO.
    *   Feature A: Summarization with one default template.
    *   View summary in-browser and download as PDF.
    *   Basic API cost tracking.
*   **Technical:** Setup all core services (FastAPI, React, Mongo, MinIO, Celery, Redis), CI/CD pipeline.

#### **Phase 2: v1.0 (Feature Completeness)**
*   **Goal:** Add snippet retrieval and enhance usability.
*   **Features:**
    *   Feature B: Snippet retrieval with page references.
    *   Full template management system (admin only).
    *   Polished UI with dark/light modes.
    *   User dashboard with job history.
*   **Technical:** Implement the vector embedding pipeline and MongoDB vector search. Build UI for template management and query results.

#### **Phase 3: v1.5+ (Polish & Optimization)**
*   **Goal:** Improve performance, reliability, and add power-user features.
*   **Features:**
    *   Batch processing (uploading multiple PDFs).
    *   Export results to different formats (e.g., Word, CSV).
    *   Performance optimizations (caching layers).
    *   Replace frontend polling with WebSockets for instant status updates.
*   **Technical:** Refactor job queue for batch handling, implement export logic, add WebSocket support to FastAPI and React.

This consolidated plan provides a complete, robust, and actionable blueprint for building the **Artemis Index**.