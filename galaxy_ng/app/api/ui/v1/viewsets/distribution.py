from rest_framework import mixins
from pulp_ansible.app import models as pulp_models
from pulpcore.plugin.util import get_objects_for_user

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui.v1 import serializers, versioning
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app import models


class DistributionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    api_base.GenericViewSet,
):
    serializer_class = serializers.DistributionSerializer
    model = pulp_models.AnsibleDistribution
    queryset = pulp_models.AnsibleDistribution.objects.exclude(
        name__endswith='-synclist').order_by('name')
    permission_classes = [access_policy.DistributionAccessPolicy]
    versioning_class = versioning.UIVersioning


class MyDistributionViewSet(DistributionViewSet):
    permission_classes = [access_policy.MyDistributionAccessPolicy]

    def get_queryset(self):
        # Optimized query using joins instead of subquery
        # This replaces the TODO comment about finding a better way to query this data
        from django.db.models import Q

        # Get user's synclists and join directly with distributions
        # This avoids the values_list subquery approach
        user_synclists = get_objects_for_user(
            self.request.user,
            'galaxy.change_synclist',
            any_perm=True,
            accept_global_perms=False,
            qs=models.SyncList.objects.select_related()
        )

        # Use a more efficient query that joins the tables directly
        synclist_names = list(user_synclists.values_list('name', flat=True))

        return pulp_models.AnsibleDistribution.objects.select_related().filter(
            name__in=synclist_names
        ).order_by('name')
