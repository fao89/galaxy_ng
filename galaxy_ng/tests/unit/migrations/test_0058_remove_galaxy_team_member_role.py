from importlib import import_module

from django.db import connection
from django.test import TestCase
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from galaxy_ng.app.models import User, Team
from galaxy_ng.app.models.organization import Organization


class TestRemoveGalaxyTeamMemberRole(TestCase):
    """
    Test cases for the migration that removes Galaxy Team Member role.

    The migration performs the following operations:
    1. Finds "Galaxy Team Member" and "Team Member" role definitions
    2. Updates all RoleUserAssignment records to use "Team Member" instead
    3. Updates all RoleTeamAssignment records to use "Team Member" instead
    4. Updates all ObjectRole records to use "Team Member" instead
    5. Deletes the "Galaxy Team Member" role definition
    """

    def _run_migration(self):
        """Run the forward migration function"""
        migration = import_module(
            "galaxy_ng.app.migrations.0058_remove_galaxy_team_member_role"
        )
        migration.remove_galaxy_team_member_role(apps, connection.schema_editor())

    def _setup_role_definitions(self):
        """Create the required role definitions for testing"""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")

        # Create Galaxy Team Member role
        galaxy_team_member_role = RoleDefinition.objects.create(
            name="Galaxy Team Member",
            description="Galaxy specific team member role",
            managed=True
        )

        # Create Team Member role
        team_member_role = RoleDefinition.objects.create(
            name="Team Member",
            description="Team member role",
            managed=True
        )

        return galaxy_team_member_role, team_member_role

    def _setup_test_data(self):
        """Create test users, teams, and organizations"""
        # Create test organization
        org = Organization.objects.create(name="Test Organization")

        # Create test team
        team = Team.objects.create(name="Test Team", organization=org)

        # Create test users
        user1 = User.objects.create(username="testuser1")
        user2 = User.objects.create(username="testuser2")

        return team, user1, user2

    def test_migration_with_galaxy_team_member_assignments(self):
        """Test migration when Galaxy Team Member role has assignments"""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
        RoleTeamAssignment = apps.get_model("dab_rbac", "RoleTeamAssignment")
        ObjectRole = apps.get_model("dab_rbac", "ObjectRole")

        # Setup role definitions and test data
        galaxy_team_member_role, team_member_role = self._setup_role_definitions()
        team, user1, user2 = self._setup_test_data()

        # Create assignments with Galaxy Team Member role
        RoleUserAssignment.objects.create(
            role_definition=galaxy_team_member_role,
            user=user1,
            object_id=team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        RoleUserAssignment.objects.create(
            role_definition=galaxy_team_member_role,
            user=user2,
            object_id=team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        RoleTeamAssignment.objects.create(
            role_definition=galaxy_team_member_role,
            team=team,
            object_id=team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        ObjectRole.objects.create(
            role_definition=galaxy_team_member_role,
            object_id=team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        # Verify initial state
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition=galaxy_team_member_role).count(),
            2
        )
        self.assertEqual(
            RoleTeamAssignment.objects.filter(role_definition=galaxy_team_member_role).count(),
            1
        )
        self.assertEqual(
            ObjectRole.objects.filter(role_definition=galaxy_team_member_role).count(),
            1
        )
        self.assertTrue(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())

        # Run migration
        self._run_migration()

        # Verify assignments were migrated to Team Member role
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition=team_member_role).count(),
            2
        )
        self.assertEqual(
            RoleTeamAssignment.objects.filter(role_definition=team_member_role).count(),
            1
        )
        self.assertEqual(
            ObjectRole.objects.filter(role_definition=team_member_role).count(),
            1
        )

        # Verify no assignments remain with Galaxy Team Member role
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition_id=galaxy_team_member_role.id).count(),
            0
        )
        self.assertEqual(
            RoleTeamAssignment.objects.filter(role_definition_id=galaxy_team_member_role.id).count(),
            0
        )
        self.assertEqual(
            ObjectRole.objects.filter(role_definition_id=galaxy_team_member_role.id).count(),
            0
        )

        # Verify Galaxy Team Member role was deleted
        self.assertFalse(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())

        # Verify Team Member role still exists
        self.assertTrue(RoleDefinition.objects.filter(name="Team Member").exists())

    def test_migration_without_galaxy_team_member_role(self):
        """Test migration when Galaxy Team Member role doesn't exist"""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")

        # Create only Team Member role (no Galaxy Team Member role)
        RoleDefinition.objects.create(
            name="Team Member",
            description="Team member role",
            managed=True
        )

        # Verify initial state
        self.assertFalse(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())
        self.assertTrue(RoleDefinition.objects.filter(name="Team Member").exists())

        # Run migration (should not fail)
        self._run_migration()

        # Verify state unchanged
        self.assertFalse(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())
        self.assertTrue(RoleDefinition.objects.filter(name="Team Member").exists())

    def test_migration_without_team_member_role(self):
        """Test migration when Team Member role doesn't exist"""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Create only Galaxy Team Member role (no Team Member role)
        galaxy_team_member_role = RoleDefinition.objects.create(
            name="Galaxy Team Member",
            description="Galaxy specific team member role",
            managed=True
        )

        # Create test data
        team, user1, user2 = self._setup_test_data()

        # Create assignment with Galaxy Team Member role
        user_assignment = RoleUserAssignment.objects.create(
            role_definition=galaxy_team_member_role,
            user=user1,
            object_id=team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        # Verify initial state
        self.assertTrue(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())
        self.assertFalse(RoleDefinition.objects.filter(name="Team Member").exists())
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition=galaxy_team_member_role).count(),
            1
        )

        # Run migration - this should handle the case gracefully
        # When team_member_role is None, the update should set role_definition_id to None
        self._run_migration()

        # Verify Galaxy Team Member role was deleted
        self.assertFalse(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())

        # Verify assignment was updated (role_definition_id should be None)
        updated_assignment = RoleUserAssignment.objects.get(id=user_assignment.id)
        self.assertIsNone(updated_assignment.role_definition_id)

    def test_migration_with_mixed_assignments(self):
        """Test migration with both Galaxy Team Member and existing Team Member assignments"""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
        RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")

        # Setup role definitions and test data
        galaxy_team_member_role, team_member_role = self._setup_role_definitions()
        team, user1, user2 = self._setup_test_data()

        # Create one assignment with Galaxy Team Member role
        RoleUserAssignment.objects.create(
            role_definition=galaxy_team_member_role,
            user=user1,
            object_id=team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        # Create one assignment with Team Member role (should remain unchanged)
        RoleUserAssignment.objects.create(
            role_definition=team_member_role,
            user=user2,
            object_id=team.id,
            content_type=ContentType.objects.get_for_model(Team)
        )

        # Verify initial state
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition=galaxy_team_member_role).count(),
            1
        )
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition=team_member_role).count(),
            1
        )

        # Run migration
        self._run_migration()

        # Verify final state - should have 2 Team Member assignments now
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition=team_member_role).count(),
            2
        )

        # Verify no Galaxy Team Member assignments remain
        self.assertEqual(
            RoleUserAssignment.objects.filter(role_definition_id=galaxy_team_member_role.id).count(),
            0
        )

        # Verify Galaxy Team Member role was deleted
        self.assertFalse(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())

    def test_migration_with_no_assignments(self):
        """Test migration when Galaxy Team Member role exists but has no assignments"""
        RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")

        # Setup role definitions
        galaxy_team_member_role, team_member_role = self._setup_role_definitions()

        # Verify initial state - roles exist but no assignments
        self.assertTrue(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())
        self.assertTrue(RoleDefinition.objects.filter(name="Team Member").exists())

        # Run migration
        self._run_migration()

        # Verify Galaxy Team Member role was deleted
        self.assertFalse(RoleDefinition.objects.filter(name="Galaxy Team Member").exists())

        # Verify Team Member role still exists
        self.assertTrue(RoleDefinition.objects.filter(name="Team Member").exists())
