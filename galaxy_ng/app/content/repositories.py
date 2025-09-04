"""
Repository management using symlinks to avoid content duplication.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from .base import BaseContentManager, ContentError, ContentNotFoundError
from .collections import CollectionManager


class ContentRepository(BaseContentManager):
    """Manages content repositories using symlinks."""
    
    def __init__(self, base_path: Optional[str] = None):
        super().__init__(base_path)
        self.repos_path = self._get_content_path('repositories')
        self.collections_manager = CollectionManager(base_path)
        self._ensure_directory(self.repos_path)
        
        # Initialize default repositories
        self._initialize_default_repos()
    
    def _initialize_default_repos(self):
        """Initialize staging and approved repositories."""
        self.create_repository('staging', {
            'name': 'staging',
            'description': 'Staging repository for collections awaiting approval',
            'pipeline': 'staging'
        })
        
        self.create_repository('approved', {
            'name': 'approved', 
            'description': 'Approved collections repository',
            'pipeline': 'approved'
        })
    
    def create_repository(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new repository."""
        repo_path = self.repos_path / name
        self._ensure_directory(repo_path)
        self._ensure_directory(repo_path / 'collections')
        
        # Store repository metadata
        repo_metadata = {
            'name': name,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        metadata_path = repo_path / 'metadata.json'
        self._write_metadata(metadata_path, repo_metadata)
        
        return repo_metadata
    
    def get_repository_metadata(self, name: str) -> Dict[str, Any]:
        """Get repository metadata."""
        repo_path = self.repos_path / name
        metadata_path = repo_path / 'metadata.json'
        
        if not metadata_path.exists():
            raise ContentNotFoundError(f"Repository {name} not found")
        
        return self._read_metadata(metadata_path)
    
    def repository_exists(self, name: str) -> bool:
        """Check if repository exists."""
        repo_path = self.repos_path / name
        return repo_path.exists() and (repo_path / 'metadata.json').exists()
    
    def add_collection_to_repository(self, repo_name: str, namespace: str, 
                                   collection: str, version: str) -> None:
        """Add a collection to repository via symlink."""
        if not self.repository_exists(repo_name):
            raise ContentNotFoundError(f"Repository {repo_name} not found")
        
        if not self.collections_manager.collection_exists(namespace, collection, version):
            raise ContentNotFoundError(f"Collection {namespace}.{collection}:{version} not found")
        
        # Get collection path
        collection_path = self.collections_manager.get_collection_path(namespace, collection, version)
        
        # Create symlink in repository
        repo_path = self.repos_path / repo_name / 'collections'
        link_path = repo_path / namespace / collection / version
        
        # Ensure parent directories exist
        self._ensure_directory(link_path.parent)
        
        # Create symlink if it doesn't exist
        if not link_path.exists():
            # Create relative symlink
            relative_target = os.path.relpath(collection_path, link_path.parent)
            link_path.symlink_to(relative_target)
    
    def remove_collection_from_repository(self, repo_name: str, namespace: str,
                                        collection: str, version: str) -> None:
        """Remove a collection from repository."""
        if not self.repository_exists(repo_name):
            raise ContentNotFoundError(f"Repository {repo_name} not found")
        
        repo_path = self.repos_path / repo_name / 'collections'
        link_path = repo_path / namespace / collection / version
        
        if link_path.is_symlink():
            link_path.unlink()
            
            # Clean up empty directories
            try:
                link_path.parent.rmdir()  # collection dir
                link_path.parent.parent.rmdir()  # namespace dir
            except OSError:
                pass  # Directories not empty
    
    def list_repository_collections(self, repo_name: str) -> List[Dict[str, str]]:
        """List all collections in a repository."""
        if not self.repository_exists(repo_name):
            return []
        
        repo_path = self.repos_path / repo_name / 'collections'
        collections = []
        
        if not repo_path.exists():
            return collections
        
        for namespace_dir in repo_path.iterdir():
            if not namespace_dir.is_dir():
                continue
                
            for collection_dir in namespace_dir.iterdir():
                if not collection_dir.is_dir():
                    continue
                    
                for version_dir in collection_dir.iterdir():
                    if version_dir.is_dir() or version_dir.is_symlink():
                        collections.append({
                            'namespace': namespace_dir.name,
                            'name': collection_dir.name,
                            'version': version_dir.name
                        })
        
        return collections
    
    def collection_in_repository(self, repo_name: str, namespace: str,
                                collection: str, version: str) -> bool:
        """Check if a collection is in a repository."""
        if not self.repository_exists(repo_name):
            return False
        
        repo_path = self.repos_path / repo_name / 'collections'
        link_path = repo_path / namespace / collection / version
        
        return link_path.exists()
    
    def promote_collection(self, namespace: str, collection: str, version: str,
                          from_repo: str = 'staging', to_repo: str = 'approved') -> None:
        """Promote a collection from one repository to another."""
        if not self.collection_in_repository(from_repo, namespace, collection, version):
            raise ContentNotFoundError(
                f"Collection {namespace}.{collection}:{version} not found in {from_repo}"
            )
        
        # Add to target repository
        self.add_collection_to_repository(to_repo, namespace, collection, version)
        
        # Note: We don't remove from source repo to maintain history
        # Collections can exist in multiple repos simultaneously
    
    def get_repository_stats(self, repo_name: str) -> Dict[str, int]:
        """Get repository statistics."""
        collections = self.list_repository_collections(repo_name)
        
        namespaces = set()
        collection_names = set()
        
        for col in collections:
            namespaces.add(col['namespace'])
            collection_names.add(f"{col['namespace']}.{col['name']}")
        
        return {
            'total_collections': len(collections),
            'unique_collections': len(collection_names),
            'namespaces': len(namespaces)
        }
    
    def search_repository_collections(self, repo_name: str, query: Optional[str] = None,
                                    namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search collections in a repository."""
        collections = self.list_repository_collections(repo_name)
        results = []
        
        for col in collections:
            # Apply filters
            if namespace and col['namespace'] != namespace:
                continue
            
            if query and query.lower() not in f"{col['namespace']}.{col['name']}".lower():
                continue
            
            # Get metadata from actual collection
            try:
                metadata = self.collections_manager.get_collection_metadata(
                    col['namespace'], col['name'], col['version']
                )
                results.append({
                    **col,
                    'metadata': metadata
                })
            except ContentNotFoundError:
                continue
        
        return results
    
    def list_repositories(self) -> List[str]:
        """List all repositories."""
        if not self.repos_path.exists():
            return []
        
        repos = []
        for repo_dir in self.repos_path.iterdir():
            if repo_dir.is_dir() and (repo_dir / 'metadata.json').exists():
                repos.append(repo_dir.name)
        
        return sorted(repos)
    
    def delete_repository(self, name: str, force: bool = False) -> None:
        """Delete a repository."""
        if not self.repository_exists(name):
            raise ContentNotFoundError(f"Repository {name} not found")
        
        # Prevent deletion of core repositories without force
        if name in ['staging', 'approved'] and not force:
            raise ContentError(f"Cannot delete core repository {name} without force=True")
        
        repo_path = self.repos_path / name
        shutil.rmtree(repo_path)
    
    def get_collection_repositories(self, namespace: str, collection: str, version: str) -> List[str]:
        """Get all repositories containing a specific collection."""
        repos = []
        
        for repo_name in self.list_repositories():
            if self.collection_in_repository(repo_name, namespace, collection, version):
                repos.append(repo_name)
        
        return repos