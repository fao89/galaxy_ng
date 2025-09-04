"""
Filesystem-based namespace model replacement.
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional

from django.db import models
from django_lifecycle import LifecycleModel
from django.conf import settings

from galaxy_ng.app.access_control import mixins
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.content.namespaces import NamespaceManager

__all__ = ("Namespace", "NamespaceLink")


class Namespace(
    LifecycleModel,
    mixins.GroupModelPermissionsMixin,
    mixins.UserModelPermissionsMixin
):
    """
    Filesystem-backed namespace model.
    
    This model maintains the same interface as the original but stores
    data on the filesystem instead of referencing Pulp objects.
    """
    
    # Core fields
    name = models.CharField(max_length=64, unique=True, blank=False)
    company = models.CharField(max_length=64, blank=True)
    email = models.CharField(max_length=256, blank=True)
    _avatar_url = models.URLField(max_length=256, blank=True)
    description = models.CharField(max_length=256, blank=True)
    resources = models.TextField(blank=True)
    
    # Tracking fields
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    # Filesystem storage flag
    _filesystem_synced = models.BooleanField(default=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._namespace_manager = NamespaceManager()
    
    @property
    def avatar_url(self):
        """Get avatar URL, checking filesystem first."""
        if settings.GALAXY_DEPLOYMENT_MODE == DeploymentMode.STANDALONE.value:
            # Check filesystem for avatar
            avatar_path = self._namespace_manager.get_namespace_avatar_path(self.name)
            if avatar_path:
                return f"{settings.ANSIBLE_API_HOSTNAME}/api/galaxy/v3/namespaces/{self.name}/avatar/"
        
        return self._avatar_url
    
    @avatar_url.setter
    def avatar_url(self, value):
        self._avatar_url = value
    
    def save(self, *args, **kwargs):
        """Save to both database and filesystem."""
        # Save to database first
        super().save(*args, **kwargs)
        
        # Sync to filesystem
        self._sync_to_filesystem()
    
    def _sync_to_filesystem(self):
        """Sync namespace data to filesystem."""
        metadata = {
            'name': self.name,
            'company': self.company,
            'email': self.email,
            'description': self.description,
            'resources': self.resources,
            'avatar_url': self._avatar_url,
            'links': {link.name: link.url for link in self.links.all()},
            'created_at': self.created.isoformat() if self.created else datetime.utcnow().isoformat(),
            'updated_at': self.updated.isoformat() if self.updated else datetime.utcnow().isoformat()
        }
        
        try:
            if self._namespace_manager.namespace_exists(self.name):
                self._namespace_manager.update_namespace_metadata(self.name, metadata)
            else:
                self._namespace_manager.create_namespace(self.name, metadata)
            
            self._filesystem_synced = True
            # Update without triggering another sync
            super().save(update_fields=['_filesystem_synced'])
            
        except Exception as e:
            # Log error but don't fail the save
            import logging
            logging.getLogger(__name__).error(f"Failed to sync namespace {self.name} to filesystem: {e}")
    
    @classmethod
    def create_from_filesystem(cls, name: str) -> 'Namespace':
        """Create namespace instance from filesystem data."""
        namespace_manager = NamespaceManager()
        
        if not namespace_manager.namespace_exists(name):
            raise ValueError(f"Namespace {name} not found on filesystem")
        
        metadata = namespace_manager.get_namespace_metadata(name)
        
        # Create or get existing instance
        instance, created = cls.objects.get_or_create(
            name=name,
            defaults={
                'company': metadata.get('company', ''),
                'email': metadata.get('email', ''),
                'description': metadata.get('description', ''),
                'resources': metadata.get('resources', ''),
                '_avatar_url': metadata.get('avatar_url', ''),
                '_filesystem_synced': True
            }
        )
        
        if not created and not instance._filesystem_synced:
            # Update existing instance with filesystem data
            instance.company = metadata.get('company', '')
            instance.email = metadata.get('email', '')
            instance.description = metadata.get('description', '')
            instance.resources = metadata.get('resources', '')
            instance._avatar_url = metadata.get('avatar_url', '')
            instance._filesystem_synced = True
            instance.save()
        
        return instance
    
    def set_links(self, links):
        """Replace namespace related links and sync to filesystem."""
        self.links.all().delete()
        self.links.bulk_create(
            NamespaceLink(name=link["name"], url=link["url"], namespace=self)
            for link in links
        )
        
        # Re-sync to filesystem with updated links
        self._sync_to_filesystem()
    
    @property
    def metadata_sha256(self):
        """Calculate metadata SHA256 from filesystem data."""
        return self._namespace_manager.calculate_metadata_sha256(self.name)
    
    def __str__(self):
        return self.name
    
    class Meta:
        permissions = (
            ('upload_to_namespace', 'Can upload collections to namespace'),
        )


class NamespaceLink(LifecycleModel):
    """
    A model representing a Namespace link.
    
    Maintains same interface but syncs to filesystem on save.
    """
    
    # Fields
    name = models.CharField(max_length=32)
    url = models.URLField(max_length=256)
    
    # References
    namespace = models.ForeignKey(
        Namespace, on_delete=models.CASCADE, related_name="links"
    )
    
    def save(self, *args, **kwargs):
        """Save and trigger namespace filesystem sync."""
        super().save(*args, **kwargs)
        # Trigger parent namespace sync
        self.namespace._sync_to_filesystem()
    
    def delete(self, *args, **kwargs):
        """Delete and trigger namespace filesystem sync."""
        namespace = self.namespace
        super().delete(*args, **kwargs)
        # Trigger parent namespace sync
        namespace._sync_to_filesystem()
    
    def __str__(self):
        return self.name