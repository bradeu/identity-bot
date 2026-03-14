# Multilingual RAG System for Political Document Analysis

A comprehensive Retrieval-Augmented Generation (RAG) system designed for processing and querying political party platform documents across multiple countries and languages. The system combines advanced AI/ML capabilities with robust document processing to enable semantic search and intelligent question-answering.

## 🌟 Features

- **Multilingual Support**: Process documents in multiple languages using BGE-M3 embeddings
- **Country-based Organization**: Separate data collections for different countries
- **Advanced PDF Processing**: Extract and analyze text, images, and tables using GPT-4o
- **Intelligent Query System**: HyDE (Hypothetical Document Embedding) with semantic reranking
- **Real-time Processing**: Asynchronous task processing with progress tracking
- **Modern Web Interface**: Next.js dashboard with drag-and-drop PDF upload
- **Scalable Architecture**: Microservices design with FastAPI and Celery

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js       │    │   FastAPI       │    │   Celery        │
│   Dashboard     │◄──►│   Backend       │◄──►│   Workers       │
│   (Frontend)    │    │   (API)         │    │   (Tasks)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   ChromaDB      │    │   MongoDB       │
                       │   (Vectors)     │    │   (Documents)   │
                       └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **Document Upload** → PDF file uploaded via dashboard
2. **Processing** → GPT-4o extracts and analyzes content
3. **Chunking** → Text split into parent-child chunks
4. **Embedding** → BGE-M3 creates multilingual embeddings
5. **Storage** → Vectors in ChromaDB, metadata in MongoDB
6. **Query** → User questions processed with HyDE and reranking
7. **Response** → GPT-4o generates contextual answers

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis server
- MongoDB server
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd code
   ```

2. **Backend Setup**
   ```bash
   cd app/backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd app/dashboard
   npm install
   ```

4. **Environment Configuration**
   ```bash
   # Create .env file in backend directory
   cd app/backend
   cp .env.example .env
   
   # Add your configuration:
   OPENAI_API_KEY=your_openai_api_key_here
   MONGO_URI=mongodb://localhost:27017
   MONGO_DB=multilingual_rag
   REDIS_URL=redis://localhost:6379
   ```

### Running the Application

**Option 1: Using the automation script (recommended)**
```bash
# From the app directory
cd app
./run.sh
```

**Option 2: Manual startup**
```bash
# Terminal 1: Start backend services
cd app/backend
./start.sh

# Terminal 2: Start frontend
cd app/dashboard
npm run dev
```

### Access Points

- **Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Base**: http://localhost:8000/api/v1

## 📖 Usage

### Document Processing

1. **Upload PDF**: Navigate to the dashboard and drag-drop a PDF file
2. **Select Country**: Choose the appropriate country from the dropdown
3. **Monitor Progress**: Watch real-time processing status updates
4. **Query Documents**: Use the search interface to ask questions

### API Integration

```python
import requests

# Upload and process a PDF
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/processor/pdf/dashboard/',
        files={'file': f},
        data={'country': 'Canada'}
    )
    task_id = response.json()['task_id']

# Monitor processing status
status_response = requests.get(f'http://localhost:8000/api/v1/tasks/status/{task_id}')
print(status_response.json())

# Query the processed documents
query_response = requests.post(
    'http://localhost:8000/api/v1/query/ask',
    json={'query': 'What are the main policy positions?', 'top_k': 3}
)
print(query_response.json())
```

## 🔧 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/` | API welcome and status |
| `GET` | `/api/v1/health/ping` | Health check |
| `POST` | `/api/v1/processor/pdf/dashboard/` | Upload and process PDF |
| `POST` | `/api/v1/query/ask` | Query documents |
| `GET` | `/api/v1/tasks/status/{task_id}` | Check task status |
| `DELETE` | `/api/v1/tasks/cancel/{task_id}` | Cancel task |

### Request/Response Examples

**Document Upload**:
```bash
curl -X POST "http://localhost:8000/api/v1/processor/pdf/dashboard/" \
  -F "file=@document.pdf" \
  -F "country=Canada"
```

**Query Documents**:
```bash
curl -X POST "http://localhost:8000/api/v1/query/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "immigration policy", "top_k": 5}'
```

## 🏢 Project Structure

```
code/
├── app/                        # Main application directory
│   ├── backend/               # FastAPI backend application
│   │   ├── api/v1/           # API endpoints
│   │   ├── service/          # Business logic layer
│   │   ├── db/               # Database layer
│   │   ├── tasks/            # Celery background tasks
│   │   ├── models/           # Pydantic models
│   │   ├── config/           # Configuration management
│   │   ├── infra/            # Infrastructure utilities
│   │   └── main.py          # Application entry point
│   ├── dashboard/            # Next.js frontend application
│   │   ├── src/app/         # App router pages
│   │   └── package.json     # Node.js dependencies
│   └── run.sh              # Application startup script
├── data/                    # Sample documents and test data
├── loadtest/               # Performance testing utilities
├── notebook/               # Jupyter notebooks for research
├── requirements.txt        # Global Python dependencies
└── README.md              # This file
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o | Required |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGO_DB` | MongoDB database name | `multilingual_rag` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379` |

### Supported Countries

The system supports 20 countries with dedicated data collections:
- Canada, United States, United Kingdom, Germany, France
- Japan, Australia, Brazil, India, South Africa
- And 10 additional countries

## 🤖 AI/ML Components

### Document Processing Pipeline

1. **PDF Extraction**: PyMuPDF extracts text, images, and tables
2. **Image Analysis**: GPT-4o vision model interprets images
3. **Table Processing**: GPT-4o analyzes and summarizes tables
4. **Text Chunking**: Parent-child chunking strategy for optimal retrieval

### Query Processing Pipeline

1. **HyDE Generation**: GPT-4o creates hypothetical document embeddings
2. **Vector Search**: ChromaDB performs cosine similarity search
3. **Reranking**: BGE-reranker-v2-m3 reorders results by relevance
4. **Answer Generation**: GPT-4o generates contextual answers

### Embedding Models

- **Text Embeddings**: BGE-M3 (multilingual, 1024 dimensions)
- **Reranking**: BGE-reranker-v2-m3
- **Language Model**: GPT-4o for analysis and generation

## 📚 Research & Development

### Jupyter Notebooks (`notebook/`)

- **`adaptive_retrieval.ipynb`**: Adaptive retrieval strategies
- **`hyde.ipynb`**: Hypothetical Document Embedding experiments
- **`pymupdf_gpt4o.ipynb`**: PDF processing with GPT-4o integration
- **`with_reranker.ipynb`**: Semantic reranking experiments
- **`small2big_*.ipynb`**: Chunking strategy research

### Load Testing (`loadtest/`)

- **Artillery**: HTTP load testing configuration
- **Flood**: Performance testing utilities
- **WRK**: Benchmarking tools

## 🔧 Development

### Backend Development

```bash
cd app/backend

# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
celery -A celery_app worker --loglevel=info
```

### Frontend Development

```bash
cd app/dashboard

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

### Testing

```bash
# Backend tests
cd app/backend
python -m pytest tests/ -v

# Load testing
cd loadtest/artillery
npm install
./run-tests.sh
```

## 📦 Deployment

### Docker Deployment

```bash
# Build backend image
cd app/backend
docker build -t multilingual-rag-backend .

# Build frontend image
cd app/dashboard
docker build -t multilingual-rag-frontend .

# Run with docker-compose
cd app
docker-compose up -d
```

### Production Considerations

- Use environment-specific configuration files
- Set up proper logging and monitoring
- Configure SSL certificates for HTTPS
- Use production-grade databases (MongoDB Atlas, Redis Cloud)
- Implement rate limiting and authentication
- Set up reverse proxy (Nginx, Cloudflare)

## 🔐 Security

### Current Security Features

- CORS configuration for cross-origin requests
- Input validation with Pydantic models
- File type validation (PDF only)
- Environment-based configuration

### Recommended Enhancements

- Implement API authentication (JWT, OAuth)
- Add rate limiting and request throttling
- Set up input sanitization and validation
- Configure secure headers and CSP
- Implement audit logging

## 🚀 Performance

### Optimization Features

- Cached service instances with `@lru_cache()`
- Asynchronous processing with Celery
- Connection pooling for databases
- Optimized chunking strategies
- Vector search with semantic reranking

### Scaling Recommendations

- Use Redis Cluster for distributed caching
- Implement horizontal scaling for Celery workers
- Consider ChromaDB clustering for large datasets
- Use CDN for frontend static assets
- Implement database sharding for high volume

## 🐛 Troubleshooting

### Common Issues

**1. FlagEmbedding Import Errors**
```bash
# The system includes fallbacks for embedding models
# Check logs for warning messages about missing dependencies
```

**2. MongoDB Connection Issues**
```bash
# Ensure MongoDB is running
mongod --dbpath /path/to/data

# Check connection string in environment variables
```

**3. Celery Task Failures**
```bash
# Check Redis connectivity
redis-cli ping

# Monitor Celery logs
celery -A celery_app worker --loglevel=debug
```

**4. PDF Processing Failures**
```bash
# Verify OpenAI API key is set
echo $OPENAI_API_KEY

# Check file permissions and format
file document.pdf
```

### Debug Mode

Enable debug logging by setting environment variables:
```bash
export CELERY_LOG_LEVEL=debug
export FASTAPI_LOG_LEVEL=debug
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript for frontend development
- Write comprehensive tests for new features
- Update documentation for API changes
- Follow semantic versioning for releases

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4o language model
- **FlagEmbedding** for multilingual embedding models
- **ChromaDB** for vector database capabilities
- **FastAPI** for modern Python web framework
- **Next.js** for React-based frontend framework
- **Celery** for distributed task processing

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the [documentation](http://localhost:8000/docs)
- Review the troubleshooting section above

---

**Built with ❤️ for political document analysis and multilingual RAG applications.**