# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) chatbot system for answering questions about course materials. It combines semantic search (ChromaDB + vector embeddings) with Claude AI's tool-calling capabilities to provide intelligent, context-aware responses about educational content.

## Essential Commands

### Setup
```bash
# Install dependencies (ALWAYS use uv, never pip)
uv sync

# Create .env file with your API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=your_key_here
```

### Running the Application
```bash
# Quick start (from project root)
./run.sh

# Manual start (ALWAYS use 'uv run', never run Python directly)
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Important**: This project uses `uv` for package management. Always use `uv run` to execute Python commands, never use `pip` directly or run Python scripts without `uv run`.

Access at: http://localhost:8000 (web UI) and http://localhost:8000/docs (API docs)

### Quality Checks

Before committing code, run quality checks:

```bash
# Run all quality checks (format, lint, type check, test)
./scripts/quality.sh

# Individual checks
./scripts/format.sh      # Format code with Ruff
./scripts/lint.sh        # Lint code
./scripts/typecheck.sh   # Type check with Mypy
./scripts/test.sh        # Run tests with coverage

# Auto-fix linting issues
cd backend && uv run ruff check --fix .
```

**Code Quality Tools:**
- **Ruff**: Fast Python formatter and linter (replaces Black, isort, Flake8)
  - Line length: 100 characters
  - Enforces PEP 8, import sorting, and code simplification
- **Mypy**: Static type checker
  - Baseline: 23 errors (documented, will be reduced incrementally)
- **Pytest with Coverage**: Test runner with coverage reporting
  - Current coverage: 64% (tests: 100%, core modules: partial)

**Before committing:**
1. Run `./scripts/quality.sh` to ensure all checks pass
2. Review coverage report at `backend/htmlcov/index.html`
3. All linting errors must be resolved
4. All tests must pass

## Architecture Overview

### Core Data Flow: Two-Stage Claude Interaction

The system uses a **tool-based RAG pattern** where Claude decides when to search:

1. **User Query** → Frontend (`script.js`) → FastAPI endpoint (`app.py:56`)
2. **RAGSystem** (`rag_system.py:102`) orchestrates the flow
3. **First Claude API call** (`ai_generator.py:80`) - Claude receives tools and decides whether to search
4. **Tool Execution** - If Claude calls `search_course_content`, it triggers:
   - `CourseSearchTool.execute()` (`search_tools.py:52`)
   - `VectorStore.search()` (`vector_store.py:61`) - semantic search via ChromaDB
   - Results formatted with course/lesson context
5. **Second Claude API call** (`ai_generator.py:134`) - Claude synthesizes answer from search results
6. **Response returned** with sources tracked through `ToolManager.last_sources`

This two-stage interaction allows Claude to autonomously decide when to search vs. answer from knowledge.

### Key Components

**RAGSystem** (`rag_system.py`) - Main orchestrator that wires together:
- DocumentProcessor: Parses course files, extracts metadata, chunks text (800 chars, 100 overlap)
- VectorStore: Manages two ChromaDB collections (`course_catalog` for titles, `course_content` for chunks)
- AIGenerator: Wraps Anthropic API with tool-use pattern
- SessionManager: Maintains conversation history (2 messages by default)
- ToolManager: Registers and executes tools (currently `search_course_content`)

**Vector Store Architecture** (`vector_store.py`):
- Two collections strategy: `course_catalog` for semantic course name matching, `course_content` for actual material
- Unified `search()` interface: resolves course names first, then searches content with filters
- Uses `all-MiniLM-L6-v2` for embeddings
- Returns `SearchResults` dataclass with documents, metadata, distances

**Document Processing** (`document_processor.py`):
- Expected format: First 3 lines have `Course Title:`, `Course Link:`, `Course Instructor:`
- Parses lesson markers: `Lesson N: [title]` followed by optional `Lesson Link:`
- Sentence-aware chunking: splits on sentence boundaries, maintains overlap, never mid-sentence
- Context enhancement: prepends `"Course {title} Lesson {N} content:"` to chunks for better retrieval

**AI Generator** (`ai_generator.py`):
- Static `SYSTEM_PROMPT` guides Claude on tool usage ("One search per query maximum")
- Handles tool execution loop: initial response → tool calls → tool results → final response
- Temperature 0, max 800 tokens for deterministic, concise answers

**Session Management** (`session_manager.py`):
- Session IDs track conversation across multiple queries
- History formatted as `"User: q\nAssistant: a"` and injected into system prompt
- `MAX_HISTORY=2` keeps last 2 exchanges (configurable in `config.py`)

### Configuration (`config.py`)

All magic numbers are centralized:
- `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100` - document processing
- `MAX_RESULTS=5` - vector search limit
- `MAX_HISTORY=2` - conversation context limit
- `CHROMA_PATH="./chroma_db"` - persistent vector storage location
- `ANTHROPIC_MODEL="claude-sonnet-4-20250514"` - Claude model version

### Frontend-Backend Contract

**POST /api/query**
```json
Request: { "query": "string", "session_id": "string|null" }
Response: { "answer": "string", "sources": ["string"], "session_id": "string" }
```

**GET /api/courses**
```json
Response: { "total_courses": int, "course_titles": ["string"] }
```

Sources are extracted from `CourseSearchTool.last_sources` and displayed in collapsible UI.

## Document Ingestion

On startup (`app.py:88`), the system:
1. Loads all `.txt`/`.pdf`/`.docx` files from `docs/` folder
2. Processes each with `DocumentProcessor.process_course_document()`
3. Stores course metadata in `course_catalog` collection
4. Stores text chunks in `course_content` collection
5. Skips courses already in database (by title)

To add new courses: place files in `docs/` and restart server.

## Important Patterns

**Tool-Based Search**: Claude uses function calling, not direct RAG. The system prompt instructs Claude to search only for course-specific questions, not general knowledge.

**Source Tracking**: `CourseSearchTool` stores sources in `self.last_sources`, which `ToolManager` retrieves after generation. Sources are reset after each query to prevent carryover.

**Two Collections Strategy**: Separating course catalog from content allows semantic course name matching ("Computer Use" matches "Building Towards Computer Use with Anthropic") before filtering content search.

**Conversation Context**: Previous exchanges are appended to system prompt, not passed as messages array, because Claude's tool-use pattern requires specific message structure.

## File Organization

```
backend/
  app.py              # FastAPI routes, startup logic
  rag_system.py       # Main orchestrator
  ai_generator.py     # Claude API wrapper
  vector_store.py     # ChromaDB interface
  document_processor.py  # Text chunking & parsing
  session_manager.py  # Conversation history
  search_tools.py     # Tool definitions for Claude
  models.py           # Pydantic models (Course, Lesson, CourseChunk)
  config.py           # Centralized configuration

frontend/
  index.html          # UI layout
  script.js           # API calls, markdown rendering (marked.js)
  style.css           # Styling

docs/                 # Course material files (auto-loaded on startup)
```

## Prerequisites

- Python 3.13+
- `uv` package manager
- Anthropic API key
- For Windows: use Git Bash for shell scripts
