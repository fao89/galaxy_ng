"""
Filesystem-based collection API endpoints.
"""
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse, Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.common.parsers import AnsibleGalaxy29MultiPartParser
from galaxy_ng.app.content.collections import CollectionManager
from galaxy_ng.app.content.repositories import ContentRepository
from galaxy_ng.app.tasks_pg.dispatcher import dispatcher
from galaxy_ng.app.tasks_pg.tasks import import_collection_to_staging, import_and_auto_approve_collection
from galaxy_ng.app.content.validation import validate_collection_artifact, CollectionValidationError


log = logging.getLogger(__name__)


class CollectionUploadViewSet(api_base.LocalSettingsMixin, viewsets.ViewSet):
    """Filesystem-based collection upload endpoint."""
    
    permission_classes = [access_policy.CollectionAccessPolicy]
    parser_classes = [AnsibleGalaxy29MultiPartParser, MultiPartParser]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection_manager = CollectionManager()
        self.repository_manager = ContentRepository()
    
    def create(self, request, *args, **kwargs):
        """Upload a collection artifact."""
        try:
            # Validate upload data
            if 'file' not in request.FILES:
                raise ValidationError(_("No file provided"))
            
            uploaded_file = request.FILES['file']
            filename = uploaded_file.name
            
            # Parse collection info from filename
            if not filename.endswith('.tar.gz'):
                raise ValidationError(_("File must be a .tar.gz archive"))
            
            # Extract namespace, name, version from filename
            # Expected format: namespace-name-version.tar.gz
            basename = filename[:-7]  # Remove .tar.gz
            parts = basename.split('-')
            if len(parts) < 3:
                raise ValidationError(_("Invalid filename format. Expected: namespace-name-version.tar.gz"))
            
            # Last part is version, second to last is name, rest is namespace
            version = parts[-1]
            name = parts[-2]
            namespace = '-'.join(parts[:-2])
            
            # Check if collection already exists
            if self.collection_manager.collection_exists(namespace, name, version):
                return Response(
                    {"detail": f"Collection {namespace}.{name}:{version} already exists"},
                    status=status.HTTP_409_CONFLICT
                )
            
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            # Optional: Quick validation before dispatching task
            # This provides faster feedback for obviously invalid files
            quick_validation = getattr(settings, 'GALAXY_QUICK_VALIDATION', True)
            if quick_validation:
                try:
                    quick_result = validate_collection_artifact(Path(tmp_path), quick_only=True)
                    if not quick_result['valid']:
                        # Clean up temp file
                        Path(tmp_path).unlink()
                        return Response(
                            {
                                "detail": "Collection validation failed",
                                "errors": quick_result['errors']
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except CollectionValidationError as e:
                    # Clean up temp file
                    Path(tmp_path).unlink()
                    return Response(
                        {
                            "detail": str(e),
                            "errors": e.errors
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Determine if auto-approval is enabled
            auto_approve = not getattr(settings, 'GALAXY_REQUIRE_CONTENT_APPROVAL', True)
            
            # Dispatch appropriate task
            if auto_approve:
                task = dispatcher.dispatch(
                    import_and_auto_approve_collection,
                    args=(tmp_path, namespace, name, version, request.user.username)
                )
            else:
                task = dispatcher.dispatch(
                    import_collection_to_staging,
                    args=(tmp_path, namespace, name, version, request.user.username)
                )
            
            # Return task info
            return Response({
                "task": str(task.pulp_id),
                "state": task.state,
                "created_at": task.pulp_created.isoformat(),
                "namespace": namespace,
                "name": name,
                "version": version
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            log.error(f"Collection upload failed: {e}")
            raise ValidationError(str(e))


class CollectionViewSet(viewsets.ViewSet):
    """Filesystem-based collection retrieval endpoints."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection_manager = CollectionManager()
        self.repository_manager = ContentRepository()
    
    def list(self, request, *args, **kwargs):
        """List collections in repository."""
        # Get repository from URL path
        distro_base_path = kwargs.get('distro_base_path', 'published')
        
        # Map distribution paths to repositories
        repo_name = 'approved' if distro_base_path == 'published' else distro_base_path
        
        # Get query parameters
        namespace = request.query_params.get('namespace')
        name = request.query_params.get('name')
        version = request.query_params.get('version')
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        if namespace and name and version:
            # Get specific collection version
            if not self.repository_manager.collection_in_repository(repo_name, namespace, name, version):
                raise NotFound(f"Collection {namespace}.{name}:{version} not found in {repo_name}")
            
            try:
                metadata = self.collection_manager.get_collection_metadata(namespace, name, version)
                return Response({
                    "meta": {"count": 1},
                    "data": [self._format_collection_response(namespace, name, version, metadata)]
                })
            except Exception:
                raise NotFound()
        
        elif namespace and name:
            # Get all versions of a collection
            versions = []
            for version_info in self.repository_manager.list_repository_collections(repo_name):
                if version_info['namespace'] == namespace and version_info['name'] == name:
                    try:
                        metadata = self.collection_manager.get_collection_metadata(
                            namespace, name, version_info['version']
                        )
                        versions.append(self._format_collection_response(
                            namespace, name, version_info['version'], metadata
                        ))
                    except Exception:
                        continue
            
            # Sort by version (latest first) and paginate
            versions.sort(key=lambda x: x['version'], reverse=True)
            paginated = versions[offset:offset + limit]
            
            return Response({
                "meta": {"count": len(versions)},
                "data": paginated
            })
        
        else:
            # List all collections
            collections = self.repository_manager.search_repository_collections(
                repo_name, namespace=namespace
            )
            
            # Group by namespace.name and get latest version
            collection_map = {}
            for col in collections:
                key = f"{col['namespace']}.{col['name']}"
                if key not in collection_map or col['version'] > collection_map[key]['version']:
                    collection_map[key] = col
            
            # Format response
            results = []
            for col in list(collection_map.values())[offset:offset + limit]:
                try:
                    formatted = self._format_collection_response(
                        col['namespace'], col['name'], col['version'], col['metadata']
                    )
                    results.append(formatted)
                except Exception:
                    continue
            
            return Response({
                "meta": {"count": len(collection_map)},
                "data": results
            })
    
    def retrieve(self, request, *args, **kwargs):
        """Get specific collection version."""
        namespace = kwargs.get('namespace')
        name = kwargs.get('name') 
        version = kwargs.get('version')
        distro_base_path = kwargs.get('distro_base_path', 'published')
        
        repo_name = 'approved' if distro_base_path == 'published' else distro_base_path
        
        if not self.repository_manager.collection_in_repository(repo_name, namespace, name, version):
            raise NotFound()
        
        try:
            metadata = self.collection_manager.get_collection_metadata(namespace, name, version)
            return Response(self._format_collection_response(namespace, name, version, metadata))
        except Exception:
            raise NotFound()
    
    @action(detail=True, methods=['get'])
    def download(self, request, *args, **kwargs):
        """Download collection artifact."""
        namespace = kwargs.get('namespace')
        name = kwargs.get('name')
        version = kwargs.get('version')
        distro_base_path = kwargs.get('distro_base_path', 'published')
        
        repo_name = 'approved' if distro_base_path == 'published' else distro_base_path
        
        if not self.repository_manager.collection_in_repository(repo_name, namespace, name, version):
            raise Http404()
        
        try:
            artifact_path = self.collection_manager.get_collection_artifact(namespace, name, version)
            
            def file_iterator(file_path, chunk_size=8192):
                with open(file_path, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            
            response = StreamingHttpResponse(
                file_iterator(artifact_path),
                content_type='application/gzip'
            )
            response['Content-Disposition'] = f'attachment; filename="{artifact_path.name}"'
            response['Content-Length'] = str(artifact_path.stat().st_size)
            
            return response
            
        except Exception:
            raise Http404()
    
    def _format_collection_response(self, namespace: str, name: str, version: str, 
                                  metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format collection for API response."""
        collection_info = metadata.get('collection_info', {})
        
        return {
            "id": f"{namespace}.{name}",
            "namespace": {
                "name": namespace
            },
            "name": name,
            "version": version,
            "certification": "published",  # All collections in approved repo are published
            "created_at": metadata.get('created_at'),
            "updated_at": metadata.get('created_at'),
            "description": collection_info.get('description', ''),
            "tags": collection_info.get('tags', []),
            "download_count": 0,  # Would need separate tracking
            "metadata": {
                "dependencies": collection_info.get('dependencies', {}),
                "documentation": collection_info.get('documentation'),
                "homepage": collection_info.get('homepage'),
                "issues": collection_info.get('issues'),
                "repository": collection_info.get('repository'),
                "tags": collection_info.get('tags', []),
            },
            "git_url": collection_info.get('repository'),
            "download_url": f"/api/galaxy/v3/collections/{namespace}/{name}/versions/{version}/download/",
            "artifact": {
                "filename": metadata.get('artifact_filename'),
                "sha256": metadata.get('sha256'),
                "size": metadata.get('size')
            }
        }