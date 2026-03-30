from google import genai
import json
from typing import Dict, Any
from models.summarize import SummarizeResponse, RepoMetadata

class GeminiClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-2.5-flash'

    async def summarize_repo(self, repo_data: Dict[str, Any]) -> SummarizeResponse:
        metadata: RepoMetadata = repo_data["metadata"]
        dir_map = repo_data["dir_map"]
        signatures = repo_data["signatures"]

        prompt = f"""
You are an expert software architect. Analyze the following GitHub repository data and provide a concise summary.

--- Layer A: Metadata & Manifests ---
Repository: {metadata.owner}/{metadata.name}
Description: {metadata.description}
Primary Language: {metadata.primary_language}
Stars: {metadata.stars}
Dependency Fingerprint: {", ".join(metadata.dependency_fingerprint)}

README Content (First 2000 chars):
{metadata.readme_content[:2000] if metadata.readme_content else "N/A"}

--- Layer C: Directory Map ---
{dir_map}

--- Layer B: Universal AST Signatures ---
{signatures}

--- Instruction ---
Based on the above information, generate a JSON response. 
Use multi-line strings for "summary" and "structure" to ensure they are readable.
Use Markdown formatting (bolding, lists, headers) within the strings.

Fields:
1. "summary": A high-level description of what the project does and its core value proposition. Use multiple paragraphs if needed.
2. "technologies": A list of the key technologies, frameworks, and libraries used.
3. "structure": A clear description of the project's architecture, key directories, and how components interact.

The response MUST be ONLY the JSON object.
"""

        try:
            # Using the new SDK's synchronous method for now since it's simpler
            # and usually used in these contexts, but it supports async too.
            # We'll use synchronous to match the existing wrapper's expectation 
            # while keeping it clean.
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            # Clean response text in case it has markdown code blocks
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
            elif "```json" in text:
                # Find the JSON part if it's wrapped in text
                import re
                match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
                if match:
                    text = match.group(1)
            
            data = json.loads(text.strip())
            return SummarizeResponse(
                summary=data["summary"],
                technologies=data["technologies"],
                structure=data["structure"]
            )
        except Exception as e:
            # Fallback in case of parsing error
            return SummarizeResponse(
                summary=f"Error analyzing repository: {str(e)}",
                technologies=[],
                structure="An error occurred during extraction."
            )
