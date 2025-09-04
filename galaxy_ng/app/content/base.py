"""
Base classes for filesystem content management.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.exceptions import ValidationError


class ContentError(Exception):
    """Base exception for content operations."""
    pass


class ContentNotFoundError(ContentError):
    """Raised when content is not found on filesystem."""
    pass


class ContentExistsError(ContentError):
    """Raised when content already exists."""
    pass


class BaseContentManager:
    """Base class for filesystem content management."""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path or getattr(settings, 'GALAXY_CONTENT_ROOT', '/content'))
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_content_path(self, *parts) -> Path:
        """Get full path for content."""
        return self.base_path.joinpath(*parts)
    
    def _ensure_directory(self, path: Path) -> None:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
    
    def _write_metadata(self, path: Path, metadata: Dict[str, Any]) -> None:
        """Write metadata to JSON file."""
        with open(path, 'w') as f:
            json.dump(metadata, f, indent=2, sort_keys=True)
    
    def _read_metadata(self, path: Path) -> Dict[str, Any]:
        """Read metadata from JSON file."""
        if not path.exists():
            raise ContentNotFoundError(f"Metadata not found: {path}")
        
        with open(path, 'r') as f:
            return json.load(f)
    
    def _calculate_file_hash(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """Calculate hash of a file."""
        hasher = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _safe_copy(self, src: Path, dst: Path) -> None:
        """Safely copy file with atomic operation."""
        dst_tmp = dst.with_suffix(dst.suffix + '.tmp')
        try:
            shutil.copy2(src, dst_tmp)
            dst_tmp.rename(dst)
        except Exception:
            if dst_tmp.exists():
                dst_tmp.unlink()
            raise
    
    def exists(self, *path_parts) -> bool:
        """Check if content exists."""
        return self._get_content_path(*path_parts).exists()


class RepositoryManager(BaseContentManager):
    """Manages repositories using symlinks to avoid content duplication."""
    
    def __init__(self, base_path: Optional[str] = None):
        super().__init__(base_path)
        self.repos_path = self._get_content_path('repositories')
        self._ensure_directory(self.repos_path)
    
    def create_repository(self, name: str) -> Path:
        """Create a new repository directory."""
        repo_path = self.repos_path / name
        self._ensure_directory(repo_path)
        return repo_path
    
    def add_content_to_repo(self, repo_name: str, content_path: Path, link_path: str) -> None:
        """Add content to repository via symlink."""
        repo_path = self.repos_path / repo_name
        link_full_path = repo_path / link_path
        
        # Ensure parent directory exists
        self._ensure_directory(link_full_path.parent)
        
        # Create symlink if it doesn't exist
        if not link_full_path.exists():
            # Make relative symlink to avoid issues with path changes
            relative_target = os.path.relpath(content_path, link_full_path.parent)
            link_full_path.symlink_to(relative_target)
    
    def remove_content_from_repo(self, repo_name: str, link_path: str) -> None:
        """Remove content from repository."""
        repo_path = self.repos_path / repo_name
        link_full_path = repo_path / link_path
        
        if link_full_path.is_symlink():
            link_full_path.unlink()
    
    def list_repo_content(self, repo_name: str) -> List[str]:
        """List all content in repository."""
        repo_path = self.repos_path / repo_name
        if not repo_path.exists():
            return []
        
        content = []
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                content.append(rel_path)
        
        return content