"""Tests related to sync ansible plugin collection content type."""
import os
import unittest
from tempfile import TemporaryDirectory
from pulp_smash.pulp3.bindings import PulpTestCase, delete_orphans, monitor_task
from pulp_smash.utils import http_get

from pulpcore.client.galaxy_ng import (
    ApiContentV3CollectionsVersionsApi,
    ApiV3NamespacesApi,
    PulpAnsibleArtifactsCollectionsV3Api,
)
from pulpcore.client.galaxy_ng.exceptions import ApiException


from galaxy_ng.tests.functional.utils import gen_galaxy_client, skip_if
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


@unittest.skip("FIXME: plugin writer action required")
class ContentUnitTestCase(PulpTestCase):
    """CRUD content unit.

    This test targets the following issues:

    * `Pulp #2872 <https://pulp.plan.io/issues/2872>`_
    * `Pulp #3445 <https://pulp.plan.io/issues/3445>`_
    * `Pulp Smash #870 <https://github.com/pulp/pulp-smash/issues/870>`_
    """

    @classmethod
    def setUpClass(cls):
        """Create class-wide variable."""
        delete_orphans()
        cls.content_unit = {}
        cls.namespace_api = ApiV3NamespacesApi(gen_galaxy_client())
        cls.cv_upload_api = PulpAnsibleArtifactsCollectionsV3Api(gen_galaxy_client())
        cls.cv_content_api = ApiContentV3CollectionsVersionsApi(gen_galaxy_client())

    @classmethod
    def tearDownClass(cls):
        """Clean class-wide variable."""
        delete_orphans()

    def upload_collection(self, namespace="pulp", name="pulp_installer", version="3.14.0"):
        """Upload collection."""
        url = f"https://galaxy.ansible.com/download/{namespace}-{name}-{version}.tar.gz"
        collection_content = http_get(url)
        self.namespace_api.create(namespace={"name": namespace, "groups": []})
        with TemporaryDirectory():
            with open(f"{namespace}-{name}-{version}.tar.gz", "wb") as tempfile:
                tempfile.write(collection_content)

            return self.cv_upload_api.create(
                f"inbound-{namespace}", file=f"{os.getcwd()}/{namespace}-{name}-{version}.tar.gz"
            )

    def test_01_create_content_unit(self):
        """Create content unit."""
        attrs = dict(namespace="pulp", name="pulp_installer", version="3.14.0")
        response = self.upload_collection(**attrs)
        created_resources = monitor_task(response.task).created_resources
        content_unit = self.cv_content_api.read(created_resources[0])
        self.content_unit.update(content_unit.to_dict())
        for key, val in attrs.items():
            with self.subTest(key=key):
                self.assertEqual(self.content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_unit(self):
        """Read a content unit by its href."""
        content_unit = self.cv_content_api.read(self.content_unit["pulp_href"]).to_dict()
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(content_unit[key], val)

    @skip_if(bool, "content_unit", False)
    def test_02_read_content_units(self):
        """Read a content unit by its pkg_id."""
        page = self.cv_content_api.list(
            namespace=self.content_unit["namespace"], name=self.content_unit["name"]
        )
        self.assertEqual(len(page.results), 1)
        for key, val in self.content_unit.items():
            with self.subTest(key=key):
                self.assertEqual(page.results[0].to_dict()[key], val)

    @skip_if(bool, "content_unit", False)
    def test_03_partially_update(self):
        """Attempt to update a content unit using HTTP PATCH.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = {"name": "testing"}
        with self.assertRaises(AttributeError) as exc:
            self.cv_content_api.partial_update(self.content_unit["pulp_href"], attrs)
        msg = "object has no attribute 'partial_update'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "content_unit", False)
    def test_03_fully_update(self):
        """Attempt to update a content unit using HTTP PUT.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = {"name": "testing"}
        with self.assertRaises(AttributeError) as exc:
            self.cv_content_api.update(self.content_unit["pulp_href"], attrs)
        msg = "object has no attribute 'update'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "content_unit", False)
    def test_04_delete(self):
        """Attempt to delete a content unit using HTTP DELETE.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        with self.assertRaises(AttributeError) as exc:
            self.cv_content_api.delete(self.content_unit["pulp_href"])
        msg = "object has no attribute 'delete'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "content_unit", False)
    def test_05_duplicate_raise_error(self):
        """Attempt to create duplicate collection."""
        attrs = dict(namespace="pulp", name="pulp_installer", version="3.14.0")
        with self.assertRaises(ApiException) as ctx:
            self.upload_collection(**attrs)
        self.assertIn(
            "The fields namespace, name, version must make a unique set.", ctx.exception.body
        )
