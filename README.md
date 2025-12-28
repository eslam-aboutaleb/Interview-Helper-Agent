# LLM-Based Interview Prep Platform v1.0

A comprehensive AI-powered interview preparation platform that generates personalized interview questions using Google's Gemini AI, with full question management, organization, and statistics tracking capabilities.

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd interview-prep-platform
   cp .env.example .env
   ```

2. **Configure Environment**
   - Edit `.env` file and add your Gemini API key:
   ```
   GEMINI_API_KEY=your-actual-gemini-api-key
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

4. **Access the Application**
   - Frontend: http://localhost:80
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Features

### Core Functionality
- **AI Question Generation**: Generate tailored interview questions using Google Gemini AI
- **Job Title Targeting**: Questions customized for specific roles (Software Engineer, Data Scientist, etc.)
- **Question Types**: Support for both technical and behavioral questions
- **Question Management**: Save, organize, edit, and delete questions
- **Rating & Flagging**: Rate difficulty and flag questions for review
- **Question Sets**: Create and manage collections of questions
- **Statistics Dashboard**: Track preparation progress with detailed analytics

### Technical Features
- **RESTful API**: Complete FastAPI backend with OpenAPI documentation
- **Real-time Updates**: Dynamic question generation and management
- **Responsive Design**: Mobile-first design that works on all devices
- **Data Persistence**: PostgreSQL database with proper schema design
- **Containerization**: Full Docker Compose setup for easy deployment
- **Error Handling**: Comprehensive error handling and validation

## Architecture

### Frontend (React SPA)
```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── pages/         # Main application pages
│   ├── services/      # API service layer
│   └── App.js         # Main application component
├── public/            # Static assets
└── Dockerfile         # Frontend container configuration
```

### Backend (FastAPI)
```
backend/
├── routes/            # API route handlers
│   ├── questions.py   # Question management endpoints
│   └── stats.py       # Statistics endpoints
├── services/          # Business logic services
│   └── gemini_service.py  # AI question generation
├── models.py          # Database models
├── schemas.py         # Pydantic schemas for validation
├── database.py        # Database configuration
└── main.py           # FastAPI application entry point
```

### Database (PostgreSQL)
```
db/
└── init.sql          # Database schema and sample data
```

## API Endpoints

### Questions
- `POST /api/questions/generate` - Generate new questions using AI
- `GET /api/questions/` - List questions with filtering options
- `GET /api/questions/{id}` - Get specific question
- `POST /api/questions/` - Create question manually
- `PUT /api/questions/{id}` - Update question
- `DELETE /api/questions/{id}` - Delete question
- `POST /api/questions/sets` - Create question set
- `GET /api/questions/sets/` - List question sets
- `POST /api/questions/rate` - Rate a question
- `GET /api/questions/job-titles/` - Get available job titles

### Statistics
- `GET /api/stats/` - Get platform statistics

### System
- `GET /` - API information
- `GET /health` - Health check endpoint

## Database Schema

### Questions Table
```sql
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    job_title VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL, -- 'technical' or 'behavioral'
    difficulty INTEGER DEFAULT 1,       -- 1-5 scale
    is_flagged BOOLEAN DEFAULT FALSE,
    tags VARCHAR(500),                  -- Comma-separated tags
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Question Sets Table
```sql
CREATE TABLE question_sets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    job_title VARCHAR(255) NOT NULL,
    question_ids TEXT,                  -- JSON array of question IDs
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### User Ratings Table
```sql
CREATE TABLE user_ratings (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL,
    rating DECIMAL(2,1) NOT NULL,       -- 1.0-5.0 scale
    feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Gemini AI Integration

The platform integrates with Google's Gemini AI for intelligent question generation:

- **Smart Prompting**: Context-aware prompts based on job title and question type
- **Structured Output**: AI responses are parsed and validated
- **Fallback System**: Mock questions when AI is unavailable
- **Error Handling**: Graceful degradation with fallback responses

### Setting Up Gemini API
1. Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Add it to your `.env` file as `GEMINI_API_KEY=your-key-here`
3. Restart the backend service

## Docker Setup

The application uses Docker Compose for easy development and deployment:

### Services
- **Frontend**: React development server (port 80)
- **Backend**: FastAPI with hot reload (port 8000)
- **Database**: PostgreSQL 15 (port 5432)

### Volumes
- `postgres_data`: Persistent database storage
- Source code volumes for hot reload during development

### Health Checks
- Database health check ensures backend starts only after DB is ready
- Backend health endpoint for monitoring

## 🔧 Development

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Local Development Setup

1. **Backend Development**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

2. **Frontend Development**
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Database Setup**
   ```bash
   docker-compose up db -d
   ```

### Environment Variables
- `GEMINI_API_KEY`: Google Gemini API key for AI question generation
- `DATABASE_URL`: PostgreSQL connection string
- `REACT_APP_API_URL`: Backend API URL for frontend

## Usage Examples

### Generating Questions
```bash
curl -X POST "http://localhost:8000/api/questions/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "job_title": "Software Engineer",
       "count": 5,
       "question_type": "mixed"
     }'
```

### Getting Statistics
```bash
curl "http://localhost:8000/api/stats/"
```

### Filtering Questions
```bash
curl "http://localhost:8000/api/questions/?job_title=Software%20Engineer&question_type=technical"
```

## Testing

The platform includes comprehensive error handling and validation:

- **Input Validation**: Pydantic schemas validate all API inputs
- **Database Constraints**: SQL constraints ensure data integrity
- **Error Responses**: Structured error messages with proper HTTP status codes
- **Health Checks**: System health monitoring endpoints

## Deployment

For production deployment:

1. **Update Environment Variables**
   - Set production database URL
   - Configure proper Gemini API key
   - Update CORS origins for frontend URL

2. **Build Production Images**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build
   ```

3. **Database Migrations**
   - Database schema is automatically created on startup
   - Sample data is inserted if tables are empty

