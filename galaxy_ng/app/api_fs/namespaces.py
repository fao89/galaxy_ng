"""
Filesystem-based namespace API endpoints.
"""
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any

from django.http import HttpResponse, Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.content.namespaces import NamespaceManager
from galaxy_ng.app.content.collections import CollectionManager
from galaxy_ng.app.tasks_pg.dispatcher import dispatcher
from galaxy_ng.app.tasks_pg.tasks import create_namespace_task, update_namespace_task


log = logging.getLogger(__name__)


class NamespaceViewSet(viewsets.ViewSet):
    """Filesystem-based namespace endpoints."""
    
    permission_classes = [access_policy.NamespaceAccessPolicy]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.namespace_manager = NamespaceManager()
        self.collection_manager = CollectionManager()
    
    def list(self, request, *args, **kwargs):
        """List namespaces."""
        query = request.query_params.get('name', '')
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        # Search namespaces
        namespaces = self.namespace_manager.search_namespaces(query if query else None)
        
        # Paginate
        total_count = len(namespaces)
        paginated = namespaces[offset:offset + limit]
        
        # Format response
        results = []
        for ns_metadata in paginated:
            results.append(self._format_namespace_response(ns_metadata))
        
        return Response({
            "meta": {
                "count": total_count
            },
            "data": results
        })
    
    def retrieve(self, request, *args, **kwargs):
        """Get specific namespace."""
        name = kwargs.get('name')
        
        if not self.namespace_manager.namespace_exists(name):
            raise NotFound(f"Namespace {name} not found")
        
        try:
            metadata = self.namespace_manager.get_namespace_metadata(name)
            return Response(self._format_namespace_response(metadata))
        except Exception as e:
            log.error(f"Error retrieving namespace {name}: {e}")
            raise NotFound()
    
    def create(self, request, *args, **kwargs):
        """Create a new namespace."""
        data = request.data
        name = data.get('name')
        
        if not name:
            raise ValidationError(_("Namespace name is required"))
        
        if self.namespace_manager.namespace_exists(name):
            return Response(
                {"detail": f"Namespace {name} already exists"},
                status=status.HTTP_409_CONFLICT
            )
        
        # Validate namespace name
        if not self._is_valid_namespace_name(name):
            raise ValidationError(_("Invalid namespace name"))
        
        # Prepare metadata
        metadata = {
            'company': data.get('company', ''),
            'email': data.get('email', ''),
            'description': data.get('description', ''),
            'resources': data.get('resources', ''),
            'avatar_url': data.get('avatar_url', ''),
            'links': data.get('links', {})
        }
        
        # Create namespace
        try:
            result = self.namespace_manager.create_namespace(name, metadata)
            return Response(
                self._format_namespace_response(result),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            log.error(f"Error creating namespace {name}: {e}")
            raise ValidationError(str(e))
    
    def update(self, request, *args, **kwargs):
        """Update namespace metadata."""
        name = kwargs.get('name')
        
        if not self.namespace_manager.namespace_exists(name):
            raise NotFound(f"Namespace {name} not found")
        
        # Update metadata
        metadata = {
            'company': request.data.get('company'),
            'email': request.data.get('email'),
            'description': request.data.get('description'),
            'resources': request.data.get('resources'),
            'avatar_url': request.data.get('avatar_url'),
            'links': request.data.get('links', {})
        }
        
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        try:
            result = self.namespace_manager.update_namespace_metadata(name, metadata)
            return Response(self._format_namespace_response(result))
        except Exception as e:
            log.error(f"Error updating namespace {name}: {e}")
            raise ValidationError(str(e))
    
    @action(detail=True, methods=['put'], parser_classes=[MultiPartParser])
    def avatar(self, request, *args, **kwargs):
        """Upload namespace avatar."""
        name = kwargs.get('name')
        
        if not self.namespace_manager.namespace_exists(name):
            raise NotFound(f"Namespace {name} not found")
        
        if 'file' not in request.FILES:
            raise ValidationError(_("No avatar file provided"))
        
        uploaded_file = request.FILES['file']
        
        # Validate file type
        allowed_types = ['.png', '.jpg', '.jpeg', '.gif', '.svg']
        file_ext = Path(uploaded_file.name).suffix.lower()
        if file_ext not in allowed_types:
            raise ValidationError(_("Invalid file type. Allowed: PNG, JPG, GIF, SVG"))
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_path = Path(tmp_file.name)
        
        try:
            # Store avatar
            avatar_url = self.namespace_manager.store_namespace_avatar(name, tmp_path)
            
            # Clean up
            tmp_path.unlink()
            
            return Response({
                "avatar_url": avatar_url
            })
            
        except Exception as e:
            # Clean up on error
            if tmp_path.exists():
                tmp_path.unlink()
            log.error(f"Error uploading avatar for namespace {name}: {e}")
            raise ValidationError(str(e))
    
    @action(detail=True, methods=['get'])
    def avatar_download(self, request, *args, **kwargs):
        """Download namespace avatar."""
        name = kwargs.get('name')
        
        avatar_path = self.namespace_manager.get_namespace_avatar_path(name)
        if not avatar_path:
            raise Http404("Avatar not found")
        
        try:
            # Determine content type
            content_type_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml'
            }
            content_type = content_type_map.get(avatar_path.suffix.lower(), 'application/octet-stream')
            
            with open(avatar_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type=content_type)
                response['Content-Disposition'] = f'inline; filename="{avatar_path.name}"'
                return response
                
        except Exception:
            raise Http404()
    
    @action(detail=True, methods=['get'])
    def collections(self, request, *args, **kwargs):
        """List collections in namespace."""
        name = kwargs.get('name')
        
        if not self.namespace_manager.namespace_exists(name):
            raise NotFound(f"Namespace {name} not found")
        
        # Get collections from filesystem
        collections = self.collection_manager.list_namespace_collections(name)
        
        # Format response
        results = []
        for collection_name in collections:
            versions = self.collection_manager.list_collection_versions(name, collection_name)
            if versions:
                try:
                    # Get latest version metadata
                    metadata = self.collection_manager.get_collection_metadata(
                        name, collection_name, versions[0]
                    )
                    collection_info = metadata.get('collection_info', {})
                    
                    results.append({
                        "name": collection_name,
                        "namespace": name,
                        "latest_version": versions[0],
                        "version_count": len(versions),
                        "description": collection_info.get('description', ''),
                        "created_at": metadata.get('created_at'),
                        "updated_at": metadata.get('created_at')
                    })
                except Exception:
                    continue
        
        return Response({
            "meta": {"count": len(results)},
            "data": results
        })
    
    def _format_namespace_response(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format namespace for API response."""
        name = metadata['name']
        
        # Get avatar URL if available
        avatar_url = metadata.get('avatar_url', '')
        if not avatar_url and self.namespace_manager.get_namespace_avatar_path(name):
            avatar_url = f"/api/galaxy/v3/namespaces/{name}/avatar/"
        
        return {
            "id": name,
            "name": name,
            "company": metadata.get('company', ''),
            "email": metadata.get('email', ''),
            "avatar_url": avatar_url,
            "description": metadata.get('description', ''),
            "resources": metadata.get('resources', ''),
            "links": metadata.get('links', {}),
            "collections_count": metadata.get('collections_count', 0),
            "created_at": metadata.get('created_at'),
            "updated_at": metadata.get('updated_at')
        }
    
    def _is_valid_namespace_name(self, name: str) -> bool:
        """Validate namespace name format."""
        import re
        # Must be lowercase alphanumeric with underscores, no leading/trailing underscores
        pattern = r'^[a-z0-9]([a-z0-9_]*[a-z0-9])?$'
        return bool(re.match(pattern, name)) and len(name) <= 64