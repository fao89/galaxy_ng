"""
Collection validation API endpoints.
"""
import logging
import tempfile
from pathlib import Path

from django.http import Http404
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.common.parsers import AnsibleGalaxy29MultiPartParser
from galaxy_ng.app.content.validation import validate_collection_artifact, CollectionValidationError
from galaxy_ng.app.tasks_pg.models import Task


log = logging.getLogger(__name__)


class CollectionValidationViewSet(viewsets.ViewSet):
    """API endpoints for collection validation."""
    
    permission_classes = [access_policy.CollectionAccessPolicy]
    parser_classes = [AnsibleGalaxy29MultiPartParser, MultiPartParser]
    
    @action(detail=False, methods=['post'])
    def validate_upload(self, request):
        """
        Validate a collection upload without storing it.
        
        This endpoint allows users to validate their collections
        before uploading them for real.
        """
        try:
            # Validate upload data
            if 'file' not in request.FILES:
                raise ValidationError(_("No file provided"))
            
            uploaded_file = request.FILES['file']
            filename = uploaded_file.name
            
            # Basic file validation
            if not filename.endswith('.tar.gz'):
                raise ValidationError(_("File must be a .tar.gz archive"))
            
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            try:
                # Run full validation
                validation_result = validate_collection_artifact(Path(tmp_path))
                
                # Format response
                response_data = {
                    "valid": validation_result['valid'],
                    "errors": validation_result.get('errors', []),
                    "warnings": validation_result.get('warnings', []),
                    "quality_score": validation_result.get('quality_score'),
                    "metadata": validation_result.get('metadata', {})
                }
                
                # Return appropriate status
                if validation_result['valid']:
                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
                    
            except CollectionValidationError as e:
                return Response({
                    "valid": False,
                    "errors": e.errors,
                    "warnings": [],
                    "quality_score": None,
                    "metadata": {},
                    "detail": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
                
            finally:
                # Clean up temporary file
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink()
                    
        except Exception as e:
            log.error(f"Validation upload failed: {e}")
            raise ValidationError(str(e))
    
    @action(detail=False, methods=['get'])
    def task_result(self, request):
        """
        Get validation results from a completed import task.
        
        Query parameters:
        - task_id: UUID of the import task
        """
        task_id = request.query_params.get('task_id')
        if not task_id:
            raise ValidationError(_("task_id parameter is required"))
        
        try:
            task = Task.objects.get(pulp_id=task_id)
        except Task.DoesNotExist:
            raise Http404("Task not found")
        
        # Check if task is completed
        if task.state not in ['completed', 'failed']:
            return Response({
                "task_id": str(task.pulp_id),
                "state": task.state,
                "validation_result": None,
                "detail": "Task not yet completed"
            })
        
        # Extract validation result from task result
        validation_result = None
        if task.state == 'completed' and task.result:
            validation_result = task.result.get('validation_result')
        elif task.state == 'failed' and task.error:
            # Check if failure was due to validation
            error_msg = task.error.get('error', '')
            if 'validation failed' in error_msg.lower():
                validation_result = {
                    "valid": False,
                    "errors": [error_msg],
                    "warnings": [],
                    "quality_score": None,
                    "metadata": {}
                }
        
        return Response({
            "task_id": str(task.pulp_id),
            "state": task.state,
            "validation_result": validation_result,
            "created_at": task.pulp_created.isoformat(),
            "finished_at": task.finished_at.isoformat() if task.finished_at else None
        })
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """
        Get current validation configuration.
        
        Returns the galaxy-importer configuration being used
        for collection validation.
        """
        from galaxy_ng.app.content.validation import validator
        
        config_info = {
            "check_required_tags": validator.config.check_required_tags,
            "check_changelog": validator.config.check_changelog,
            "check_runtime": validator.config.check_runtime,
            "require_v1_or_greater": validator.config.require_v1_or_greater,
            "check_flake8": validator.config.check_flake8,
            "check_ansible_lint": validator.config.check_ansible_lint,
            "check_yamllint": validator.config.check_yamllint,
            "max_file_size": validator.config.max_file_size,
            "max_total_size": validator.config.max_total_size
        }
        
        return Response({
            "validation_config": config_info,
            "galaxy_importer_version": self._get_importer_version()
        })
    
    def _get_importer_version(self) -> str:
        """Get galaxy-importer version."""
        try:
            import galaxy_importer
            return getattr(galaxy_importer, '__version__', 'unknown')
        except ImportError:
            return 'not_installed'