"""
Task functions for filesystem operations using PostgreSQL task system.
"""
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from ..content.collections import CollectionManager
from ..content.namespaces import NamespaceManager
from ..content.repositories import ContentRepository
from ..content.validation import validate_collection_artifact, CollectionValidationError
from .registry import task


logger = logging.getLogger(__name__)


@task()
def import_collection_to_staging(artifact_path: str, namespace: str, name: str,
                                version: str, username: str) -> Dict[str, Any]:
    """Import a collection to staging repository with validation."""
    collection_manager = CollectionManager()
    repository_manager = ContentRepository()
    
    artifact_file = Path(artifact_path)
    
    try:
        logger.info(f"Starting import of {namespace}.{name}:{version} to staging")
        
        # Step 1: Validate collection using galaxy-importer
        logger.info(f"Validating collection artifact: {artifact_file}")
        validation_result = validate_collection_artifact(artifact_file)
        
        if not validation_result['valid']:
            error_msg = f"Collection validation failed: {validation_result['errors']}"
            logger.error(error_msg)
            raise CollectionValidationError(error_msg, validation_result['errors'])
        
        logger.info(f"Collection validation successful for {namespace}.{name}:{version}")
        
        # Step 2: Store collection with validation metadata
        metadata = {
            'uploaded_by': username,
            'repository': 'staging',
            'validation_result': validation_result,
            'importer_metadata': validation_result.get('metadata', {}),
            'quality_score': validation_result.get('quality_score'),
            'warnings': validation_result.get('warnings', [])
        }
        
        collection_metadata = collection_manager.store_collection(
            namespace, name, version, artifact_file, metadata
        )
        
        # Step 3: Add to staging repository
        repository_manager.add_collection_to_repository('staging', namespace, name, version)
        
        logger.info(f"Successfully imported {namespace}.{name}:{version} to staging")
        
        return {
            'namespace': namespace,
            'name': name,
            'version': version,
            'metadata': collection_metadata,
            'validation_result': validation_result
        }
        
    except CollectionValidationError:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        logger.error(f"Error importing collection {namespace}.{name}:{version}: {e}")
        raise
    finally:
        # Clean up temporary file
        if artifact_file.exists():
            artifact_file.unlink()


@task()
def import_and_auto_approve_collection(artifact_path: str, namespace: str, name: str,
                                     version: str, username: str) -> Dict[str, Any]:
    """Import collection with validation and auto-approve to published repository."""
    logger.info(f"Starting import and auto-approve of {namespace}.{name}:{version}")
    
    # First import to staging (includes validation)
    result = import_collection_to_staging(artifact_path, namespace, name, version, username)
    
    # If validation passed and collection is in staging, promote to approved
    repository_manager = ContentRepository()
    repository_manager.promote_collection(namespace, name, version, 'staging', 'approved')
    
    logger.info(f"Auto-approved {namespace}.{name}:{version} to published repository")
    
    result['auto_approved'] = True
    return result


@task()
def promote_collection_task(namespace: str, name: str, version: str, 
                           from_repo: str = 'staging', to_repo: str = 'approved') -> Dict[str, Any]:
    """Promote collection between repositories."""
    repository_manager = ContentRepository()
    repository_manager.promote_collection(namespace, name, version, from_repo, to_repo)
    
    return {
        'namespace': namespace,
        'name': name,
        'version': version,
        'promoted_from': from_repo,
        'promoted_to': to_repo
    }


@task()
def delete_collection_task(namespace: str, name: str, version: str) -> Dict[str, Any]:
    """Delete a collection version."""
    collection_manager = CollectionManager()
    repository_manager = ContentRepository()
    
    # Remove from all repositories first
    for repo_name in repository_manager.list_repositories():
        if repository_manager.collection_in_repository(repo_name, namespace, name, version):
            repository_manager.remove_collection_from_repository(repo_name, namespace, name, version)
    
    # Delete the actual collection
    collection_manager.delete_collection(namespace, name, version)
    
    return {
        'namespace': namespace,
        'name': name,
        'version': version,
        'deleted': True
    }


@task()
def create_namespace_task(name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new namespace."""
    namespace_manager = NamespaceManager()
    result = namespace_manager.create_namespace(name, metadata)
    
    return result


@task()
def update_namespace_task(name: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Update namespace metadata."""
    namespace_manager = NamespaceManager()
    result = namespace_manager.update_namespace_metadata(name, metadata)
    
    return result


@task()
def cleanup_orphaned_content() -> Dict[str, Any]:
    """Clean up orphaned content not referenced by any repository."""
    collection_manager = CollectionManager()
    repository_manager = ContentRepository()
    
    cleaned_collections = []
    
    # Find collections not in any repository
    for namespace in collection_manager.collection_manager.namespaces_path.iterdir():
        if not namespace.is_dir():
            continue
            
        for collection_dir in namespace.iterdir():
            if not collection_dir.is_dir() or collection_dir.name == 'metadata.json':
                continue
                
            versions_dir = collection_dir / 'versions'
            if not versions_dir.exists():
                continue
                
            for version_dir in versions_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                
                # Check if this collection version is in any repository
                in_repos = repository_manager.get_collection_repositories(
                    namespace.name, collection_dir.name, version_dir.name
                )
                
                if not in_repos:
                    # Orphaned collection, mark for cleanup
                    cleaned_collections.append({
                        'namespace': namespace.name,
                        'name': collection_dir.name,
                        'version': version_dir.name
                    })
                    
                    # Delete orphaned content
                    collection_manager.delete_collection(
                        namespace.name, collection_dir.name, version_dir.name
                    )
    
    return {
        'cleaned_collections': cleaned_collections,
        'total_cleaned': len(cleaned_collections)
    }


@task()
def validate_existing_collection(namespace: str, name: str, version: str) -> Dict[str, Any]:
    """Validate an existing collection that's already stored."""
    collection_manager = CollectionManager()
    
    if not collection_manager.collection_exists(namespace, name, version):
        raise ValueError(f"Collection {namespace}.{name}:{version} not found")
    
    try:
        # Get collection artifact path
        artifact_path = collection_manager.get_collection_artifact(namespace, name, version)
        
        # Run validation
        validation_result = validate_collection_artifact(artifact_path)
        
        # Update collection metadata with validation results
        existing_metadata = collection_manager.get_collection_metadata(namespace, name, version)
        existing_metadata.update({
            'validation_result': validation_result,
            'importer_metadata': validation_result.get('metadata', {}),
            'quality_score': validation_result.get('quality_score'),
            'warnings': validation_result.get('warnings', []),
            'revalidated_at': datetime.utcnow().isoformat()
        })
        
        # Store updated metadata
        collection_path = collection_manager.get_collection_path(namespace, name, version)
        metadata_path = collection_path / 'metadata.json'
        collection_manager._write_metadata(metadata_path, existing_metadata)
        
        return {
            'namespace': namespace,
            'name': name,
            'version': version,
            'validation_result': validation_result,
            'revalidated': True
        }
        
    except CollectionValidationError as e:
        return {
            'namespace': namespace,
            'name': name,
            'version': version,
            'validation_result': {
                'valid': False,
                'errors': e.errors,
                'warnings': [],
                'quality_score': None,
                'metadata': {}
            },
            'revalidated': True,
            'validation_failed': True
        }


@task()
def bulk_validate_collections(repository: str = None) -> Dict[str, Any]:
    """Validate all collections in a repository or all collections."""
    collection_manager = CollectionManager()
    repository_manager = ContentRepository()
    
    validated_collections = []
    failed_validations = []
    
    if repository:
        # Validate collections in specific repository
        collections = repository_manager.list_repository_collections(repository)
    else:
        # Validate all collections
        collections = []
        for namespace in collection_manager.list_namespace_collections(''):
            for collection_name in collection_manager.list_namespace_collections(namespace):
                versions = collection_manager.list_collection_versions(namespace, collection_name)
                for version in versions:
                    collections.append({
                        'namespace': namespace,
                        'name': collection_name,
                        'version': version
                    })
    
    for collection in collections:
        try:
            result = validate_existing_collection(
                collection['namespace'],
                collection['name'], 
                collection['version']
            )
            
            if result.get('validation_failed'):
                failed_validations.append(result)
            else:
                validated_collections.append(result)
                
        except Exception as e:
            failed_validations.append({
                'namespace': collection['namespace'],
                'name': collection['name'],
                'version': collection['version'],
                'error': str(e)
            })
    
    return {
        'repository': repository,
        'total_collections': len(collections),
        'validated_successfully': len(validated_collections),
        'validation_failures': len(failed_validations),
        'failed_collections': failed_validations
    }


@task()
def repair_repository_links() -> Dict[str, Any]:
    """Repair broken symlinks in repositories."""
    repository_manager = ContentRepository()
    
    repaired_links = []
    
    for repo_name in repository_manager.list_repositories():
        repo_collections_path = repository_manager.repos_path / repo_name / 'collections'
        
        if not repo_collections_path.exists():
            continue
        
        # Walk through all symlinks in repository
        for root, dirs, files in repo_collections_path.walk():
            for item in dirs + files:
                item_path = Path(root) / item
                
                if item_path.is_symlink() and not item_path.exists():
                    # Broken symlink, try to repair
                    try:
                        # Extract namespace, collection, version from path
                        relative_path = item_path.relative_to(repo_collections_path)
                        parts = relative_path.parts
                        
                        if len(parts) >= 3:
                            namespace, collection, version = parts[0], parts[1], parts[2]
                            
                            # Check if target content exists
                            if repository_manager.collections_manager.collection_exists(
                                namespace, collection, version
                            ):
                                # Remove broken link and recreate
                                item_path.unlink()
                                repository_manager.add_collection_to_repository(
                                    repo_name, namespace, collection, version
                                )
                                
                                repaired_links.append({
                                    'repository': repo_name,
                                    'namespace': namespace,
                                    'collection': collection,
                                    'version': version
                                })
                            else:
                                # Target doesn't exist, remove broken link
                                item_path.unlink()
                                
                    except Exception as e:
                        # Log error but continue
                        import logging
                        logging.getLogger(__name__).error(
                            f"Failed to repair link {item_path}: {e}"
                        )
    
    return {
        'repaired_links': repaired_links,
        'total_repaired': len(repaired_links)
    }