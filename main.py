import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from models.summarize import SummarizeRequest, SummarizeResponse
from engine.github_client import GitHubClient
from engine.signature_engine import SignatureEngine
from engine.repo_processor import RepoProcessor
from llm.gemini_client import GeminiClient

load_dotenv()

app = FastAPI(title="GitHub Repository Summarizer")

# Global instances (simplified for demo)
github_token = os.getenv("GITHUB_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    # Use a dummy or throw warning, but the prompt says MUST use GEMINI_API_KEY
    print("WARNING: GEMINI_API_KEY not set.")

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    gh_client = GitHubClient(token=github_token)
    sig_engine = SignatureEngine()
    processor = RepoProcessor(gh_client, sig_engine)
    
    try:
        # Layer 1, 2, 3 Extraction
        repo_data = await processor.process_repo(request.github_url)
        
        # LLM Summarization
        if not gemini_api_key:
             raise HTTPException(status_code=500, detail="GEMINI_API_KEY is missing from environment.")
             
        llm_client = GeminiClient(gemini_api_key)
        summary = await llm_client.summarize_repo(repo_data)
        
        # Return indented JSON for readability
        import json
        from fastapi.responses import Response
        return Response(
            content=json.dumps(summary.model_dump(), indent=4),
            media_type="application/json"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    finally:
        await gh_client.close()

@app.get("/")
def root():
    return {
        "message": "Welcome to the GitHub Repository Summarizer API",
        "endpoints": {
            "summarize": "/summarize (POST)",
            "health": "/health (GET)",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}
