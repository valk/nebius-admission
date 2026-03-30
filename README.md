# GitHub Repository Summarizer

A FastAPI service that provides insightful summaries of GitHub repositories using Gemini 1.5 Pro and a specialized AST-based signature extraction strategy to handle large codebases within context limits.

## Features
- **Layer A**: Extracts repository metadata, README, and dependency fingerprints from manifest files (e.g., `package.json`, `requirements.txt`).
- **Layer B (Signature Engine)**: Uses **Tree-sitter** to perform AST-based signature extraction, capturing only class and function definitions (signatures + docstrings) while discarding implementation bodies. This reduces tokens by ~10x.
- **Layer C**: Generates a 3-level deep directory tree map.
- **Concurrent Processing**: Uses `asyncio` and `httpx` for high-performance file fetching.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- A Gemini API Key (Get one at [Google AI Studio](https://aistudio.google.com/))

### 2. Installation
```bash
# Clone the repository (if applicable)
cd github-repo-summarizer

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: GITHUB_TOKEN=your_github_token_for_higher_rate_limits
```

### 4. Running the Server
```bash
uvicorn main:app --reload
```

## How to Test

### 1. Using Interactive Documentation (Fastest)
FastAPI provides a built-in UI for testing:
1. Open **[http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)** in your browser.
2. Expand the **POST `/summarize`** endpoint.
3. Click **"Try it out"**.
4. Enter a GitHub URL:
   ```json
   {
     "github_url": "https://github.com/fastapi/fastapi"
   }
   ```
5. Click **"Execute"**.

### 2. Using CURL
Run this in your terminal:
```bash
curl -X POST "http://127.0.0.1:8080/summarize" \
     -H "Content-Type: application/json" \
     -d '{"github_url": "https://github.com/psf/requests"}'
```

## API Usage

### Summarize a Repository
**Endpoint**: `POST /summarize`

**Request Body**:
```json
{
  "github_url": "https://github.com/fastapi/fastapi"
}
```

**Response**:
```json
{
  "summary": "...",
  "technologies": ["...", "..."],
  "structure": "..."
}
```

## Architecture Approach

### Universal Signature Extraction (The "Signature Engine")
To solve the "Context Window" challenge, this service implements a specialized pre-processing pipeline. Instead of sending raw code files to the LLM, we use **Tree-sitter** to parse source code (supporting Python, JS, Go, Rust, etc.) and extract only:
- Class definitions
- Function signatures (names + arguments)
- Docstrings and leading comments

By discarding function bodies and internal implementation logic, we can pack 10x more high-signal code information into the Gemini context window, allowing for better analysis of large repositories.

### Model Choice: Gemini 1.5 Pro
Gemini 1.5 Pro was chosen for its **massive context window** (up to 2M tokens) and exceptional **reasoning capabilities** for complex code analysis. Its ability to handle large amounts of data while maintaining high performance makes it ideal for synthesizing repository-wide summaries.

## Evaluation
The server handles public repositories and provides 4xx errors for private or invalid URLs. It uses concurrent fetching to minimize latency.
