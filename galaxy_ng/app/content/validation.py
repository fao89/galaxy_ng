"""
Collection validation using galaxy-importer.
"""
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

from galaxy_importer import main as importer_main
from galaxy_importer.config import Config
from galaxy_importer.exceptions import ImporterError


logger = logging.getLogger(__name__)


class CollectionValidationError(Exception):
    """Collection validation failed."""
    
    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.errors = errors or []


class CollectionValidator:
    """Validates collections using galaxy-importer."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or self._get_default_config()
    
    def _get_default_config(self) -> Config:
        """Get default galaxy-importer configuration."""
        config = Config()
        
        # Configure importer settings
        config.check_required_tags = True
        config.check_changelog = True
        config.check_runtime = True
        config.require_v1_or_greater = True
        config.local_image_build = False
        config.check_flake8 = True
        config.check_ansible_lint = True
        config.check_yamllint = True
        
        # Set file size limits
        config.max_file_size = 1024 * 1024 * 10  # 10MB
        config.max_total_size = 1024 * 1024 * 50  # 50MB
        
        return config
    
    def validate_collection(self, artifact_path: Path) -> Dict[str, Any]:
        """
        Validate a collection artifact using galaxy-importer.
        
        Args:
            artifact_path: Path to collection tar.gz file
            
        Returns:
            Validation result with metadata and any errors
            
        Raises:
            CollectionValidationError: If validation fails
        """
        if not artifact_path.exists():
            raise CollectionValidationError(f"Collection artifact not found: {artifact_path}")
        
        if not artifact_path.name.endswith('.tar.gz'):
            raise CollectionValidationError("Collection must be a .tar.gz archive")
        
        logger.info(f"Validating collection: {artifact_path}")
        
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Run galaxy-importer
                result = importer_main.import_collection(
                    filename=str(artifact_path),
                    output_dir=str(temp_path),
                    config=self.config
                )
                
                # Check for validation errors
                errors = []
                warnings = []
                
                if hasattr(result, 'errors') and result.errors:
                    errors.extend(result.errors)
                
                if hasattr(result, 'warnings') and result.warnings:
                    warnings.extend(result.warnings)
                
                # Convert importer result to our format
                validation_result = {
                    'valid': len(errors) == 0,
                    'errors': errors,
                    'warnings': warnings,
                    'metadata': self._extract_metadata(result),
                    'quality_score': getattr(result, 'quality_score', None)
                }
                
                # If there are errors, raise validation error
                if errors:
                    error_messages = [str(error) for error in errors]
                    raise CollectionValidationError(
                        f"Collection validation failed: {'; '.join(error_messages)}",
                        errors=errors
                    )
                
                logger.info(f"Collection validation successful: {artifact_path}")
                return validation_result
                
            except ImporterError as e:
                logger.error(f"Galaxy-importer error: {e}")
                raise CollectionValidationError(f"Import validation failed: {str(e)}")
            
            except Exception as e:
                logger.error(f"Unexpected validation error: {e}")
                raise CollectionValidationError(f"Validation error: {str(e)}")
    
    def _extract_metadata(self, importer_result) -> Dict[str, Any]:
        """Extract metadata from galaxy-importer result."""
        metadata = {}
        
        if hasattr(importer_result, 'metadata') and importer_result.metadata:
            metadata = importer_result.metadata.copy()
        
        # Extract common fields
        if hasattr(importer_result, 'name'):
            metadata['name'] = importer_result.name
        
        if hasattr(importer_result, 'namespace'):
            metadata['namespace'] = importer_result.namespace
        
        if hasattr(importer_result, 'version'):
            metadata['version'] = importer_result.version
        
        if hasattr(importer_result, 'description'):
            metadata['description'] = importer_result.description
        
        if hasattr(importer_result, 'tags'):
            metadata['tags'] = importer_result.tags
        
        if hasattr(importer_result, 'dependencies'):
            metadata['dependencies'] = importer_result.dependencies
        
        if hasattr(importer_result, 'documentation'):
            metadata['documentation'] = importer_result.documentation
        
        if hasattr(importer_result, 'homepage'):
            metadata['homepage'] = importer_result.homepage
        
        if hasattr(importer_result, 'issues'):
            metadata['issues'] = importer_result.issues
        
        if hasattr(importer_result, 'repository'):
            metadata['repository'] = importer_result.repository
        
        if hasattr(importer_result, 'license'):
            metadata['license'] = importer_result.license
        
        if hasattr(importer_result, 'authors'):
            metadata['authors'] = importer_result.authors
        
        return metadata
    
    def quick_validate(self, artifact_path: Path) -> bool:
        """
        Quick validation check - just verify it's a valid collection archive.
        
        Args:
            artifact_path: Path to collection tar.gz file
            
        Returns:
            True if basic validation passes
        """
        try:
            import tarfile
            
            # Check if it's a valid tar.gz
            if not tarfile.is_tarfile(artifact_path):
                return False
            
            # Check for required files
            with tarfile.open(artifact_path, 'r:gz') as tar:
                files = tar.getnames()
                
                # Must have galaxy.yml or MANIFEST.json
                has_galaxy_yml = any(f.endswith('galaxy.yml') for f in files)
                has_manifest = any(f.endswith('MANIFEST.json') for f in files)
                
                return has_galaxy_yml or has_manifest
                
        except Exception as e:
            logger.warning(f"Quick validation failed: {e}")
            return False


# Global validator instance
validator = CollectionValidator()


def validate_collection_artifact(artifact_path: Path, 
                                quick_only: bool = False) -> Dict[str, Any]:
    """
    Validate a collection artifact.
    
    Args:
        artifact_path: Path to collection tar.gz file
        quick_only: If True, only do basic validation
        
    Returns:
        Validation result
        
    Raises:
        CollectionValidationError: If validation fails
    """
    if quick_only:
        is_valid = validator.quick_validate(artifact_path)
        return {
            'valid': is_valid,
            'errors': [] if is_valid else ['Invalid collection archive'],
            'warnings': [],
            'metadata': {},
            'quality_score': None
        }
    else:
        return validator.validate_collection(artifact_path)