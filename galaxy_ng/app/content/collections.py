"""
Collection filesystem management.
"""
import tarfile
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .base import BaseContentManager, ContentError, ContentNotFoundError, ContentExistsError


class CollectionManager(BaseContentManager):
    """Manages Ansible collections on the filesystem."""
    
    def __init__(self, base_path: Optional[str] = None):
        super().__init__(base_path)
        self.collections_path = self._get_content_path('collections')
        self._ensure_directory(self.collections_path)
    
    def get_collection_path(self, namespace: str, name: str, version: str) -> Path:
        """Get the path for a specific collection version."""
        return self.collections_path / namespace / name / 'versions' / version
    
    def get_namespace_path(self, namespace: str) -> Path:
        """Get the path for a namespace."""
        return self.collections_path / namespace
    
    def collection_exists(self, namespace: str, name: str, version: str) -> bool:
        """Check if a collection version exists."""
        collection_path = self.get_collection_path(namespace, name, version)
        return collection_path.exists() and (collection_path / 'metadata.json').exists()
    
    def store_collection(self, namespace: str, name: str, version: str, 
                        artifact_file: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Store a collection artifact and metadata."""
        collection_path = self.get_collection_path(namespace, name, version)
        
        if self.collection_exists(namespace, name, version):
            raise ContentExistsError(f"Collection {namespace}.{name}:{version} already exists")
        
        # Create directory structure
        self._ensure_directory(collection_path)
        
        # Store artifact
        artifact_name = f"{namespace}-{name}-{version}.tar.gz"
        artifact_dest = collection_path / artifact_name
        self._safe_copy(artifact_file, artifact_dest)
        
        # Calculate checksums
        sha256_hash = self._calculate_file_hash(artifact_dest, 'sha256')
        
        # Extract and validate collection metadata from artifact
        collection_info = self._extract_collection_info(artifact_dest)
        
        # Prepare full metadata
        full_metadata = {
            'namespace': namespace,
            'name': name,
            'version': version,
            'artifact_filename': artifact_name,
            'sha256': sha256_hash,
            'size': artifact_dest.stat().st_size,
            'created_at': datetime.utcnow().isoformat(),
            'collection_info': collection_info,
            **metadata
        }
        
        # Store metadata
        metadata_path = collection_path / 'metadata.json'
        self._write_metadata(metadata_path, full_metadata)
        
        return full_metadata
    
    def get_collection_metadata(self, namespace: str, name: str, version: str) -> Dict[str, Any]:
        """Get collection metadata."""
        collection_path = self.get_collection_path(namespace, name, version)
        metadata_path = collection_path / 'metadata.json'
        return self._read_metadata(metadata_path)
    
    def get_collection_artifact(self, namespace: str, name: str, version: str) -> Path:
        """Get collection artifact file path."""
        if not self.collection_exists(namespace, name, version):
            raise ContentNotFoundError(f"Collection {namespace}.{name}:{version} not found")
        
        collection_path = self.get_collection_path(namespace, name, version)
        artifact_name = f"{namespace}-{name}-{version}.tar.gz"
        return collection_path / artifact_name
    
    def list_collection_versions(self, namespace: str, name: str) -> List[str]:
        """List all versions of a collection."""
        collection_base = self.collections_path / namespace / name / 'versions'
        if not collection_base.exists():
            return []
        
        versions = []
        for version_dir in collection_base.iterdir():
            if version_dir.is_dir() and (version_dir / 'metadata.json').exists():
                versions.append(version_dir.name)
        
        return sorted(versions, reverse=True)  # Latest first
    
    def list_namespace_collections(self, namespace: str) -> List[str]:
        """List all collections in a namespace."""
        namespace_path = self.get_namespace_path(namespace)
        if not namespace_path.exists():
            return []
        
        collections = []
        for collection_dir in namespace_path.iterdir():
            if collection_dir.is_dir() and collection_dir.name != 'metadata.json':
                # Check if it has any versions
                versions_path = collection_dir / 'versions'
                if versions_path.exists() and any(versions_path.iterdir()):
                    collections.append(collection_dir.name)
        
        return sorted(collections)
    
    def delete_collection(self, namespace: str, name: str, version: str) -> None:
        """Delete a collection version."""
        collection_path = self.get_collection_path(namespace, name, version)
        if collection_path.exists():
            shutil.rmtree(collection_path)
    
    def search_collections(self, query: Optional[str] = None, 
                          namespace: Optional[str] = None,
                          tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search collections based on criteria."""
        results = []
        
        # Get namespaces to search
        if namespace:
            namespaces = [namespace] if self.get_namespace_path(namespace).exists() else []
        else:
            namespaces = [d.name for d in self.collections_path.iterdir() 
                         if d.is_dir()]
        
        for ns in namespaces:
            collections = self.list_namespace_collections(ns)
            
            for collection in collections:
                versions = self.list_collection_versions(ns, collection)
                if not versions:
                    continue
                
                # Get latest version metadata
                try:
                    metadata = self.get_collection_metadata(ns, collection, versions[0])
                    
                    # Apply filters
                    if query and query.lower() not in f"{ns}.{collection}".lower():
                        if 'description' in metadata and query.lower() not in metadata['description'].lower():
                            continue
                    
                    if tags and 'collection_info' in metadata:
                        collection_tags = metadata['collection_info'].get('tags', [])
                        if not any(tag in collection_tags for tag in tags):
                            continue
                    
                    results.append({
                        'namespace': ns,
                        'name': collection,
                        'latest_version': versions[0],
                        'versions': versions,
                        'metadata': metadata
                    })
                    
                except ContentNotFoundError:
                    continue
        
        return results
    
    def _extract_collection_info(self, artifact_path: Path) -> Dict[str, Any]:
        """Extract galaxy.yml/MANIFEST.json from collection artifact."""
        try:
            with tarfile.open(artifact_path, 'r:gz') as tar:
                # Try to find galaxy.yml first
                galaxy_yml = None
                manifest_json = None
                
                for member in tar.getnames():
                    if member.endswith('galaxy.yml'):
                        galaxy_yml = member
                        break
                    elif member.endswith('MANIFEST.json'):
                        manifest_json = member
                
                if galaxy_yml:
                    with tar.extractfile(galaxy_yml) as f:
                        return yaml.safe_load(f.read())
                elif manifest_json:
                    with tar.extractfile(manifest_json) as f:
                        import json
                        return json.loads(f.read())
                else:
                    return {}
                    
        except Exception as e:
            raise ContentError(f"Failed to extract collection info: {e}")
    
    def get_download_stats(self, namespace: str, name: str) -> Dict[str, int]:
        """Get download statistics for a collection."""
        # This would be implemented with a separate stats tracking system
        # For now, return empty stats
        return {
            'total_downloads': 0,
            'monthly_downloads': 0,
            'weekly_downloads': 0
        }