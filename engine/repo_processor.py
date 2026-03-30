import asyncio
from typing import List, Dict, Any, Optional
from engine.github_client import GitHubClient
from engine.signature_engine import SignatureEngine
from models.summarize import RepoMetadata

class RepoProcessor:
    def __init__(self, github_client: GitHubClient, sig_engine: SignatureEngine):
        self.github_client = github_client
        self.sig_engine = sig_engine
        self.ignore_patterns = [
            "node_modules", ".git", "lockfile", ".bin", "vendor", 
            "__pycache__", ".ipynb_checkpoints", "dist", "build"
        ]
        self.manifest_files = [
            "package.json", "requirements.txt", "go.mod", "Cargo.toml",
            "Gemfile", "pom.xml", "build.gradle", "pyproject.toml"
        ]

    async def process_repo(self, url: str) -> Dict[str, Any]:
        # Layer A: Metadata & Manifests
        metadata = await self.github_client.get_repo_metadata(url)
        tree = await self.github_client.get_repo_tree(metadata.owner, metadata.name)
        
        # Layer C: Directory Map (Max 3 levels)
        dir_map = self._generate_dir_map(tree, max_depth=3)
        
        # Identify relevant files
        readme_path = next((f["path"] for f in tree if f["path"].lower() == "readme.md"), None)
        manifest_paths = [f["path"] for f in tree if f["path"] in self.manifest_files]
        
        # Layer B: AST Extraction - identify source files
        source_extensions = [".py", ".js", ".ts", ".go", ".rs", ".cpp", ".c", ".java"]
        source_paths = [
            f["path"] for f in tree 
            if any(f["path"].endswith(ext) for ext in source_extensions)
            and not any(p in f["path"] for p in self.ignore_patterns)
        ]
        
        # Limit source files to avoid huge payloads (e.g., top 15-20 files or by relevance)
        source_paths = source_paths[:30] 

        # Concurrent fetching
        tasks = []
        if readme_path:
            tasks.append(self.github_client.get_file_content(metadata.owner, metadata.name, readme_path))
        else:
            tasks.append(asyncio.sleep(0, result=""))
            
        for path in manifest_paths:
            tasks.append(self.github_client.get_file_content(metadata.owner, metadata.name, path))
            
        for path in source_paths:
            tasks.append(self.github_client.get_file_content(metadata.owner, metadata.name, path))
            
        results = await asyncio.gather(*tasks)
        
        # Process results
        idx = 0
        if readme_path:
            metadata.readme_content = results[idx]
            idx += 1
        else:
            idx += 1
            
        manifest_contents = results[idx : idx + len(manifest_paths)]
        metadata.dependency_fingerprint = self._extract_dependencies(manifest_paths, manifest_contents)
        idx += len(manifest_paths)
        
        source_contents = results[idx:]
        signatures = []
        for path, code in zip(source_paths, source_contents):
            if code:
                sig = self.sig_engine.extract_signatures(path, code)
                if sig:
                    signatures.append(f"--- File: {path} ---\n{sig}")

        return {
            "metadata": metadata,
            "dir_map": dir_map,
            "signatures": "\n\n".join(signatures)
        }

    def _generate_dir_map(self, tree: List[Dict[str, Any]], max_depth: int) -> str:
        lines = []
        for item in tree:
            path = item["path"]
            depth = path.count("/") + 1
            if depth <= max_depth:
                if any(p in path for p in self.ignore_patterns):
                    continue
                indent = "  " * (depth - 1)
                lines.append(f"{indent}- {path.split('/')[-1]} ({item['type']})")
        return "\n".join(lines)

    def _extract_dependencies(self, paths: List[str], contents: List[str]) -> List[str]:
        fingerprint = []
        for path, content in zip(paths, contents):
            if not content: continue
            if path == "package.json":
                # Simple parsing or use json
                import json
                try:
                    data = json.loads(content)
                    deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
                    fingerprint.extend(deps[:10]) # Top 10
                except: pass
            elif path == "requirements.txt":
                deps = [line.split("==")[0].split(">=")[0].strip() for line in content.splitlines() if line and not line.startswith("#")]
                fingerprint.extend(deps[:10])
            else:
                fingerprint.append(path) # Just note the presence of other manifests
        return list(set(fingerprint))
