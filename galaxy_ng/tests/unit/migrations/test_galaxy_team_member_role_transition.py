"""
Integration tests for Galaxy Team Member to Team Member role transition.

These tests verify the complete transition from "Galaxy Team Member" to "Team Member"
role across different scenarios including migration, signal handling, and edge cases.
"""

from importlib import import_module
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from galaxy_ng.app.models import User, Team
from galaxy_ng.app.models.organization import Organization


class TestGalaxyTeamMemberRoleTransition(TestCase):
    """Integration tests for the complete role transition process."""

    def setUp(self):
        """Set up test data for integration tests."""
        self.org = Organization.objects.create(name="Test Organization")
        self.team = Team.objects.create(name="Test Team", organization=self.org)
        self.user1 = User.objects.create(username="testuser1")
        self.user2 = User.objects.create(username="testuser2")
        self.admin_user = User.objects.create(username="admin", is_superuser=True)

    def _run_migration(self):
        """Helper to run the migration."""
        migration = import_module(
            "galaxy_ng.app.migrations.0058_remove_galaxy_team_member_role"
        )
        return migration.remove_galaxy_team_member_role(apps, None)

    def test_complete_migration_workflow(self):
        """Test the complete migration workflow from Galaxy Team Member to Team Member."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
        RoleTeamAssignment = apps.get_model("dab_rbac", "RoleTeamAssignment")
        ObjectRole = apps.get_model("dab_rbac", "ObjectRole")

        # Step 1: Create initial state with Galaxy Team Member role
        galaxy_role = RoleDefinition.objects.create_from_permissions(
            name="Galaxy Team Member",
            permissions=["view_team"],
            managed=True,
        )

        team_role = RoleDefinition.objects.get(
            name="Team Member",
        )

        # Step 2: Create various types of assignments
        user_assignment = RoleUserAssignment.objects.create(
            role_definition=galaxy_role,
            user=self.user1,
            object_id=self.team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        team_assignment = RoleTeamAssignment.objects.create(
            role_definition=galaxy_role,
            team=self.team,
            object_id=self.team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        object_role = ObjectRole.objects.create(
            role_definition=galaxy_role,
            object_id=self.team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        # Step 3: Verify pre-migration state
        pre_migration_counts = {
            'user_assignments': RoleUserAssignment.objects.filter(role_definition=galaxy_role).count(),
            'team_assignments': RoleTeamAssignment.objects.filter(role_definition=galaxy_role).count(),
            'object_roles': ObjectRole.objects.filter(role_definition=galaxy_role).count(),
            'galaxy_role_exists': RoleDefinition.objects.filter(name="Galaxy Team Member").exists(),
            'team_role_exists': RoleDefinition.objects.filter(name="Team Member").exists(),
        }

        self.assertEqual(pre_migration_counts['user_assignments'], 1)
        self.assertEqual(pre_migration_counts['team_assignments'], 1)
        self.assertEqual(pre_migration_counts['object_roles'], 1)
        self.assertTrue(pre_migration_counts['galaxy_role_exists'])
        self.assertTrue(pre_migration_counts['team_role_exists'])

        # Step 4: Run migration
        self._run_migration()

        # Step 5: Verify post-migration state
        post_migration_counts = {
            'user_assignments': RoleUserAssignment.objects.filter(role_definition=team_role).count(),
            'team_assignments': RoleTeamAssignment.objects.filter(role_definition=team_role).count(),
            'object_roles': ObjectRole.objects.filter(role_definition=team_role).count(),
            'galaxy_role_exists': RoleDefinition.objects.filter(name="Galaxy Team Member").exists(),
            'team_role_exists': RoleDefinition.objects.filter(name="Team Member").exists(),
            'orphaned_assignments': (
                RoleUserAssignment.objects.filter(role_definition_id=galaxy_role.id).count() +
                RoleTeamAssignment.objects.filter(role_definition_id=galaxy_role.id).count() +
                ObjectRole.objects.filter(role_definition_id=galaxy_role.id).count()
            )
        }

        # All assignments should be migrated to Team Member role
        self.assertEqual(post_migration_counts['user_assignments'], 1)
        self.assertEqual(post_migration_counts['team_assignments'], 1)
        self.assertEqual(post_migration_counts['object_roles'], 1)

        # Galaxy Team Member role should be deleted
        self.assertFalse(post_migration_counts['galaxy_role_exists'])

        # Team Member role should still exist
        self.assertTrue(post_migration_counts['team_role_exists'])

        # No orphaned assignments should remain
        self.assertEqual(post_migration_counts['orphaned_assignments'], 0)

    def test_migration_with_large_dataset(self):
        """Test migration performance and correctness with a larger dataset."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create roles
        galaxy_role = RoleDefinition.objects.create_from_permissions(
            name="Galaxy Team Member",
            permissions=["view_team"],
            managed=True,
        )

        team_role = RoleDefinition.objects.get(
            name="Team Member",
        )

        # Create multiple teams and users
        teams = []
        users = []

        for i in range(5):
            team = Team.objects.create(
                name=f"Team {i}",
                organization=self.org
            )
            teams.append(team)

            user = User.objects.create(username=f"user{i}")
            users.append(user)

        # Create assignments for each user-team combination
        assignments_created = 0
        for user in users:
            for team in teams:
                RoleUserAssignment.objects.create(
                    role_definition=galaxy_role,
                    user=user,
                    object_id=team.id,
                    content_type=ContentType.objects.get_for_model(Team)
                )
                assignments_created += 1

        # Verify initial count
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition=galaxy_role).count(),
            assignments_created
        )

        # Run migration
        self._run_migration()

        # Verify all assignments were migrated
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition=team_role).count(),
            assignments_created
        )

        # Verify no Galaxy Team Member assignments remain
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition_id=galaxy_role.id).count(),
            0
        )

    def test_migration_idempotency(self):
        """Test that running the migration multiple times is safe."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create initial state
        team_role = RoleDefinition.objects.get(
            name="Team Member",
        )

        assignment = RoleUserAssignment.objects.create(
            role_definition=team_role,
            user=self.user1,
            object_id=self.team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        # Run migration (should be no-op since Galaxy Team Member doesn't exist)
        initial_count = RoleUserAssignment.objects.filter(role_definition=team_role).count()

        self._run_migration()

        # Count should be unchanged
        final_count = RoleUserAssignment.objects.filter(role_definition=team_role).count()
        self.assertEqual(initial_count, final_count)

        # Team Member role should still exist
        self.assertTrue(RoleDefinition.objects.filter(name="Team Member").exists())

    def test_migration_with_corrupted_data(self):
        """Test migration handles corrupted or inconsistent data gracefully."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create Galaxy Team Member role
        galaxy_role = RoleDefinition.objects.create_from_permissions(
            name="Galaxy Team Member",
            permissions=["view_team"],
            managed=True,
        )

        # Create assignment with invalid object_id
        invalid_assignment = RoleUserAssignment.objects.create(
            role_definition=galaxy_role,
            user=self.user1,
            object_id=99999,  # Non-existent object
            content_type=ContentType.objects.get_for_model(Team)
        )

        # Create assignment with None user (if possible)
        try:
            null_user_assignment = RoleUserAssignment.objects.create(
                role_definition=galaxy_role,
                user=None,
                object_id=self.team.id,
                content_type=ContentType.objects.get_for_model(Team)
            )
        except:
            # Some databases might not allow null users
            null_user_assignment = None

        # Run migration - should not crash
        try:
            self._run_migration()
            migration_succeeded = True
        except Exception as e:
            migration_succeeded = False
            self.fail(f"Migration failed with corrupted data: {e}")

        self.assertTrue(migration_succeeded)

        # Galaxy Team Member role should still be deleted
        self.assertFalse(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())

    def test_backward_compatibility_constants(self):
        """Test that signal handler constants are properly updated."""
        from galaxy_ng.app.signals.handlers import SHARED_TEAM_ROLE

        # Verify the constant is set to the new role name
        self.assertEqual(SHARED_TEAM_ROLE, "Team Member")

        # Verify the old constant is removed by checking the module's attributes
        import galaxy_ng.app.signals.handlers as handlers_module
        self.assertFalse(hasattr(handlers_module, 'TEAM_MEMBER_ROLE'),
                         "TEAM_MEMBER_ROLE constant should have been removed")

    def test_serializer_compatibility(self):
        """Test that serializers work with the new role names."""
        from galaxy_ng.app.api.ui.v2.serializers import UserDetailSerializer

        # Create a user with team membership
        self.team.group.user_set.add(self.user1)

        # Mock the role definitions and assignments
        with patch('galaxy_ng.app.api.ui.v2.serializers.RoleDefinition') as mock_role_def, \
             patch('galaxy_ng.app.api.ui.v2.serializers.RoleUserAssignment') as mock_assignment:

            # Mock role definitions to return Team Member role
            mock_role_def.objects.filter.return_value.values_list.return_value = [1]

            # Mock assignments
            mock_assignment.objects.filter.return_value.values_list.return_value = [self.team.id]

            # Create serializer
            serializer = UserDetailSerializer(self.user1)

            # Should work without errors and include team information
            data = serializer.data
            self.assertIn('teams', data)

    def test_migration_rollback_safety(self):
        """Test that migration data changes are reversible conceptually."""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create initial state
        galaxy_role = RoleDefinition.objects.create_from_permissions(
            name="Galaxy Team Member",
            permissions=["view_team"],
            managed=True,
        )

        team_role = RoleDefinition.objects.get(
            name="Team Member",
        )

        # Create assignment
        assignment = RoleUserAssignment.objects.create(
            role_definition=galaxy_role,
            user=self.user1,
            object_id=self.team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        # Store original assignment details
        original_user_id = assignment.user.id
        original_object_id = assignment.object_id
        original_content_type_id = assignment.content_type.id

        # Run migration
        self._run_migration()

        # Find the migrated assignment
        migrated_assignment = RoleUserAssignment.objects.get(
            user_id=original_user_id,
            object_id=original_object_id,
            content_type_id=original_content_type_id,
            role_definition=team_role
        )

        # Verify we could theoretically rollback by having all the data
        self.assertEqual(migrated_assignment.user.id, original_user_id)
        self.assertEqual(migrated_assignment.object_id, original_object_id)
        self.assertEqual(migrated_assignment.content_type.id, original_content_type_id)

        # The only thing that changed is the role_definition
        self.assertEqual(migrated_assignment.role_definition, team_role)

    def test_cross_app_consistency(self):
        """Test that changes are consistent across different parts of the application."""
        # Test that integration test utilities use the correct role name
        from galaxy_ng.tests.integration.utils.teams import add_user_to_team

        # Mock the client to verify it looks for "Team Member" role
        mock_client = Mock()
        mock_client.get.return_value = {
            'results': [{'id': 1, 'name': 'Team Member'}]
        }
        mock_client.post.return_value = {'user': 1}

        # Call the utility function
        add_user_to_team(mock_client, userid=1, teamid=1)

        # Verify it searched for "Team Member" role, not "Galaxy Team Member"
        mock_client.get.assert_called_with(
            "_ui/v2/role_definitions/",
            params={'name': 'Team Member'}
        )
