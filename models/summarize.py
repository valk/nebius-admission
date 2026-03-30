from pydantic import BaseModel, HttpUrl
from typing import List

class SummarizeRequest(BaseModel):
    github_url: str

class SummarizeResponse(BaseModel):
    summary: str
    technologies: List[str]
    structure: str

class RepoMetadata(BaseModel):
    name: str
    owner: str
    description: str | None
    primary_language: str | None
    stars: int
    readme_content: str | None = None
    dependency_fingerprint: List[str] = []
