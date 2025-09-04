"""
Namespace filesystem management.
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import BaseContentManager, ContentNotFoundError


class NamespaceManager(BaseContentManager):
    """Manages Ansible namespaces on the filesystem."""
    
    def __init__(self, base_path: Optional[str] = None):
        super().__init__(base_path)
        self.namespaces_path = self._get_content_path('collections')
        self._ensure_directory(self.namespaces_path)
    
    def get_namespace_path(self, name: str) -> Path:
        """Get the path for a namespace."""
        return self.namespaces_path / name
    
    def namespace_exists(self, name: str) -> bool:
        """Check if a namespace exists."""
        namespace_path = self.get_namespace_path(name)
        return namespace_path.exists()
    
    def create_namespace(self, name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new namespace with metadata."""
        namespace_path = self.get_namespace_path(name)
        self._ensure_directory(namespace_path)
        
        # Prepare namespace metadata
        full_metadata = {
            'name': name,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            **metadata
        }
        
        # Store metadata
        metadata_path = namespace_path / 'metadata.json'
        self._write_metadata(metadata_path, full_metadata)
        
        return full_metadata
    
    def get_namespace_metadata(self, name: str) -> Dict[str, Any]:
        """Get namespace metadata."""
        namespace_path = self.get_namespace_path(name)
        metadata_path = namespace_path / 'metadata.json'
        
        if not metadata_path.exists():
            # Return minimal metadata if file doesn't exist
            return {
                'name': name,
                'company': '',
                'email': '',
                'description': '',
                'resources': '',
                'avatar_url': '',
                'links': {},
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
        
        return self._read_metadata(metadata_path)
    
    def update_namespace_metadata(self, name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update namespace metadata."""
        if not self.namespace_exists(name):
            raise ContentNotFoundError(f"Namespace {name} not found")
        
        # Get existing metadata
        existing_metadata = self.get_namespace_metadata(name)
        
        # Update with new data
        existing_metadata.update(metadata)
        existing_metadata['updated_at'] = datetime.utcnow().isoformat()
        
        # Store updated metadata
        namespace_path = self.get_namespace_path(name)
        metadata_path = namespace_path / 'metadata.json'
        self._write_metadata(metadata_path, existing_metadata)
        
        return existing_metadata
    
    def store_namespace_avatar(self, name: str, avatar_file: Path) -> str:
        """Store namespace avatar and return the URL path."""
        if not self.namespace_exists(name):
            raise ContentNotFoundError(f"Namespace {name} not found")
        
        namespace_path = self.get_namespace_path(name)
        
        # Determine file extension
        extension = avatar_file.suffix or '.png'
        avatar_dest = namespace_path / f'avatar{extension}'
        
        # Copy avatar file
        self._safe_copy(avatar_file, avatar_dest)
        
        # Calculate SHA256 for caching
        avatar_sha256 = self._calculate_file_hash(avatar_dest, 'sha256')
        
        # Update metadata with avatar info
        metadata = self.get_namespace_metadata(name)
        metadata['avatar_sha256'] = avatar_sha256
        metadata['avatar_filename'] = f'avatar{extension}'
        self.update_namespace_metadata(name, metadata)
        
        return f'/api/galaxy/v3/namespaces/{name}/avatar/'
    
    def get_namespace_avatar_path(self, name: str) -> Optional[Path]:
        """Get the path to namespace avatar file."""
        if not self.namespace_exists(name):
            return None
        
        namespace_path = self.get_namespace_path(name)
        metadata = self.get_namespace_metadata(name)
        
        if 'avatar_filename' in metadata:
            avatar_path = namespace_path / metadata['avatar_filename']
            if avatar_path.exists():
                return avatar_path
        
        # Check for common avatar files
        for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
            avatar_path = namespace_path / f'avatar{ext}'
            if avatar_path.exists():
                return avatar_path
        
        return None
    
    def list_namespaces(self) -> List[str]:
        """List all namespaces."""
        if not self.namespaces_path.exists():
            return []
        
        namespaces = []
        for namespace_dir in self.namespaces_path.iterdir():
            if namespace_dir.is_dir():
                namespaces.append(namespace_dir.name)
        
        return sorted(namespaces)
    
    def get_namespace_collections_count(self, name: str) -> int:
        """Get the number of collections in a namespace."""
        if not self.namespace_exists(name):
            return 0
        
        namespace_path = self.get_namespace_path(name)
        count = 0
        
        for item in namespace_path.iterdir():
            if item.is_dir() and item.name != 'metadata.json':
                # Check if it has versions directory with content
                versions_path = item / 'versions'
                if versions_path.exists() and any(versions_path.iterdir()):
                    count += 1
        
        return count
    
    def delete_namespace(self, name: str, force: bool = False) -> None:
        """Delete a namespace."""
        if not self.namespace_exists(name):
            raise ContentNotFoundError(f"Namespace {name} not found")
        
        namespace_path = self.get_namespace_path(name)
        
        # Check if namespace has collections
        if not force and self.get_namespace_collections_count(name) > 0:
            raise ContentError(f"Namespace {name} contains collections. Use force=True to delete.")
        
        shutil.rmtree(namespace_path)
    
    def calculate_metadata_sha256(self, name: str) -> str:
        """Calculate SHA256 hash of namespace metadata for consistency checking."""
        metadata = self.get_namespace_metadata(name)
        
        # Create consistent metadata for hashing
        hash_metadata = {
            'name': metadata.get('name', ''),
            'company': metadata.get('company', ''),
            'email': metadata.get('email', ''),
            'description': metadata.get('description', ''),
            'resources': metadata.get('resources', ''),
            'links': metadata.get('links', {}),
            'avatar_sha256': metadata.get('avatar_sha256')
        }
        
        metadata_json = json.dumps(hash_metadata, sort_keys=True).encode('utf-8')
        hasher = hashlib.sha256(metadata_json)
        return hasher.hexdigest()
    
    def search_namespaces(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search namespaces."""
        results = []
        
        for namespace_name in self.list_namespaces():
            try:
                metadata = self.get_namespace_metadata(namespace_name)
                
                # Apply search filter
                if query:
                    searchable_text = f"{namespace_name} {metadata.get('company', '')} {metadata.get('description', '')}"
                    if query.lower() not in searchable_text.lower():
                        continue
                
                # Add collection count
                metadata['collections_count'] = self.get_namespace_collections_count(namespace_name)
                results.append(metadata)
                
            except Exception:
                continue
        
        return results