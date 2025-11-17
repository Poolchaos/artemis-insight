# Artemis Insight

> AI-powered document intelligence platform for automated summarization and analysis

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.3-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115-green.svg)](https://fastapi.tiangolo.com/)

Artemis Insight transforms lengthy technical documents into structured, actionable summaries using AI. Upload PDFs, select a template, and receive comprehensive summaries organized by your specifications.

## ✨ Features

### 📄 Document Processing
- **PDF Upload & Analysis** - Upload and process PDF documents up to 50MB
- **Intelligent Text Extraction** - Extract text with metadata preservation
- **Vector Embeddings** - Create searchable embeddings for semantic analysis
- **Multi-pass Processing** - Configurable chunk sizes and overlap for optimal results

### 🎯 Template-Based Summarization
- **Custom Templates** - Define section structures with guidance prompts
- **Section Ordering** - Control the flow and organization of summaries
- **Required Fields** - Mark critical sections for mandatory completion
- **Reusable Templates** - Create once, use for multiple documents

### 📊 Summary Management
- **Status Tracking** - Monitor processing, completed, and failed summaries
- **Section Breakdown** - View detailed content by section with page references
- **Export Options** - Download summaries as PDF or Word documents
- **Markdown Support** - Rich text formatting with headers, bold, and lists

### 🎨 Modern UI/UX
- **Dark Mode** - Comfortable viewing in any lighting condition
- **Responsive Design** - Works seamlessly on desktop and tablet
- **Real-time Updates** - Live status monitoring during processing
- **Modal Dialogs** - Professional confirmations and error messages

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API Key
- 8GB RAM minimum
- 10GB free disk space

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Poolchaos/artemis-insight.git
   cd artemis-insight
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set your OpenAI API key:
   ```env
   OPENAI_API_KEY=sk-your-api-key-here
   ```

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8001
   - API Docs: http://localhost:8001/docs

### First Steps

1. **Create a Template**
   - Navigate to Templates → Create New Template
   - Define sections with guidance prompts
   - Set section order and required fields

2. **Upload a Document**
   - Go to Documents → Upload
   - Select a PDF file
   - Wait for processing to complete

3. **Generate a Summary**
   - Click "Process" on a document
   - Select your template
   - Monitor progress in Summaries

4. **Export Results**
   - Open the completed summary
   - Click Export → Choose PDF or DOCX
   - Download and share

## 🏗️ Architecture

### Technology Stack

**Frontend**
- React 18 with TypeScript
- TailwindCSS for styling
- Zustand for state management
- React Router for navigation
- Heroicons for icons

**Backend**
- FastAPI (Python 3.11)
- MongoDB for data storage
- Redis for caching
- Celery for async tasks
- MinIO for file storage

**AI/ML**
- OpenAI GPT-4o-mini for summarization
- OpenAI text-embedding-3-small for embeddings
- PDFPlumber for text extraction
- ReportLab for PDF generation
- python-docx for Word exports

### System Components

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│   Nginx     │────▶│   FastAPI   │
│  (React)    │     │  (Frontend) │     │  (Backend)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────────┐
                    │                          │              │
              ┌─────▼─────┐            ┌──────▼──────┐  ┌───▼────┐
              │  MongoDB  │            │   Celery    │  │ MinIO  │
              │ (Database)│            │  (Workers)  │  │(Storage)│
              └───────────┘            └─────────────┘  └────────┘
                                              │
                                       ┌──────▼──────┐
                                       │    Redis    │
                                       │   (Queue)   │
                                       └─────────────┘
```

## 📁 Project Structure

```
artemis-insight/
├── backend/
│   ├── app/
│   │   ├── models/          # Pydantic models & MongoDB schemas
│   │   ├── routes/          # FastAPI route handlers
│   │   ├── services/        # Business logic
│   │   ├── middleware/      # Auth & CORS
│   │   ├── tasks.py         # Celery async tasks
│   │   └── main.py          # FastAPI app initialization
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API clients
│   │   ├── stores/          # Zustand stores
│   │   └── types/           # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔧 Configuration

### Environment Variables

**Required:**
```env
OPENAI_API_KEY=sk-...          # Your OpenAI API key
```

**Database:**
```env
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=secure_password
MONGO_DATABASE=artemis_insight
```

**Storage:**
```env
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=secure_password
MINIO_BUCKET=artemis-insight
```

**Authentication:**
```env
JWT_SECRET_KEY=your-secret-key  # Generate with: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Processing Configuration

Adjust template processing strategies in the template configuration:

```json
{
  "processing_strategy": {
    "approach": "multi-pass",
    "chunk_size": 600,
    "overlap": 75,
    "embedding_model": "text-embedding-3-small",
    "summarization_model": "gpt-4o-mini"
  }
}
```

## 📖 Usage Examples

### Template Structure

Example template for a feasibility study:

```json
{
  "name": "Feasibility Study Summary",
  "description": "Technical summary for engineering review",
  "sections": [
    {
      "title": "Executive Summary",
      "order": 1,
      "required": true,
      "guidance_prompt": "Synthesize key findings, proposed solution, and recommendations"
    },
    {
      "title": "Technical Aspects",
      "order": 2,
      "required": true,
      "guidance_prompt": "Describe components, sizing, operations, and implementation"
    },
    {
      "title": "Cost Analysis",
      "order": 3,
      "required": true,
      "guidance_prompt": "Extract capital costs, operating costs, and unit reference values"
    }
  ]
}
```

### API Examples

**Upload a document:**
```bash
curl -X POST http://localhost:8001/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf"
```

**Create a summary:**
```bash
curl -X POST "http://localhost:8001/api/summaries?document_id=xxx&template_id=yyy" \
  -H "Authorization: Bearer $TOKEN"
```

**Export as PDF:**
```bash
curl -X GET "http://localhost:8001/api/summaries/{summary_id}/export/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -o summary.pdf
```

## 🧪 Development

### Running Locally

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Worker:**
```bash
cd backend
celery -A app.celery_app worker --loglevel=info
```

### Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

### Code Quality

```bash
# Backend linting
cd backend
flake8 app/
black app/
isort app/

# Frontend linting
cd frontend
npm run lint
npm run format
```

## 🐛 Troubleshooting

### Common Issues

**"Failed to connect to MongoDB"**
- Ensure MongoDB container is running: `docker ps`
- Check credentials in `.env` match `docker-compose.yml`
- Verify port 27017 is not in use

**"OpenAI API rate limit"**
- Check your OpenAI account has sufficient credits
- Reduce concurrent processing in template strategy
- Consider using GPT-3.5-turbo for faster processing

**"PDF upload fails"**
- Check file size is under 50MB
- Ensure MinIO container is healthy
- Verify MINIO_BUCKET exists

**"Summary shows 0 sections"**
- Confirm template has sections defined (not legacy fields)
- Check template was saved correctly in MongoDB
- Refresh browser cache

### Logs

```bash
# View all logs
docker-compose logs -f

# Specific service logs
docker logs artemis-insight-backend --tail 100
docker logs artemis-insight-celery-worker --tail 100
docker logs artemis-insight-frontend --tail 100

# Database logs
docker logs artemis-insight-mongodb --tail 50
```

## 📝 Changelog

### [Unreleased]

### [0.2.0] - 2025-11-17

**Added:**
- Summary list page with status filtering
- Detailed summary view with section breakdown
- PDF and DOCX export functionality
- ProcessPage for document summarization workflow
- Markdown rendering in summaries
- Modal dialogs for confirmations and errors
- Local 24-hour time format
- Human-readable processing time display

**Changed:**
- Replaced browser alerts with modal components
- Updated template types for backward compatibility
- Improved error messages and validation
- Enhanced dark mode support

**Fixed:**
- ObjectId conversion bug in summary endpoints
- PDF markdown parsing with proper regex
- Template edit form not populating sections
- CORS headers for file downloads
- TypeScript compilation errors in templates

### [0.1.0] - 2025-11-15

**Added:**
- Initial release
- Document upload and processing
- Template management
- Basic summarization
- User authentication
- Dark mode support

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) for GPT-4 and embeddings
- [FastAPI](https://fastapi.tiangolo.com/) for the amazing web framework
- [React](https://reactjs.org/) for the UI library
- [TailwindCSS](https://tailwindcss.com/) for styling utilities

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Poolchaos/artemis-insight/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Poolchaos/artemis-insight/discussions)
- **Email**: support@artemisinnovations.co.za

## 🗺️ Roadmap

- [ ] Multi-document batch processing
- [ ] Custom AI model selection per template
- [ ] Collaborative editing and sharing
- [ ] Advanced analytics dashboard
- [ ] API webhooks for integrations
- [ ] Multi-language support
- [ ] Mobile app (iOS/Android)
- [ ] On-premise deployment option

---

**Built with ❤️ by [Artemis Innovations](https://artemisinnovations.co.za)**
