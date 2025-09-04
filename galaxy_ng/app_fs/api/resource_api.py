"""
Resource API configuration for filesystem deployment.
Simplified version without pulpcore dependencies.
"""
from ansible_base.resource_registry.registry import (
    ResourceConfig,
    ServiceAPIConfig,
    SharedResource,
)
from ansible_base.resource_registry.shared_types import OrganizationType, TeamType, UserType

from galaxy_ng.app_fs import models


class APIConfig(ServiceAPIConfig):
    service_type = "galaxy"


RESOURCE_LIST = (
    ResourceConfig(
        models.User,
        shared_resource=SharedResource(serializer=UserType, is_provider=False),
        name_field="username",
    ),
    ResourceConfig(
        models.Team,
        shared_resource=SharedResource(serializer=TeamType, is_provider=True),
        name_field="name",
    ),
    ResourceConfig(
        models.Organization,
        shared_resource=SharedResource(serializer=OrganizationType, is_provider=False),
        name_field="name",
    ),
)