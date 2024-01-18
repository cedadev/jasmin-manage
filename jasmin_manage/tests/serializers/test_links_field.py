from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from ...models import Consortium, Project
from ...serializers.base import LinksField


class LinksFieldTestCase(TestCase):
    """
    Tests for the links serializer field.
    """

    maxDiff = None

    def test_init_kwargs(self):
        # Tests that the field correctly requests the whole object and is read-only
        field = LinksField()
        self.assertEqual(field.source, "*")
        self.assertTrue(field.read_only)

    def test_bind_model_serializer(self):
        # Test that bind generates the correct lists of views for links to be created from
        # when given a model serializer
        serializer = type(
            "ProjectSerializer",
            (serializers.ModelSerializer,),
            {"Meta": type("Meta", (), {"model": Project})},
        )
        field = LinksField()
        field.bind("_links", serializer)
        # Check that the basename was inferred correctly
        self.assertEqual(field.basename, "project")
        # Check that the urlconf was inferred correctly
        self.assertEqual(field.urlconf, "jasmin_manage.urls")
        # Check that the related object links were generated correctly
        self.assertCountEqual(
            field.related_object_links,
            [("consortium", "consortium-detail", "consortium_id")],
        )
        # Check that the related list links were generated correctly
        self.assertCountEqual(
            field.related_list_links,
            [
                ("collaborators", "project-collaborators-list"),
                ("comments", "project-comments-list"),
                ("invitations", "project-invitations-list"),
                ("services", "project-services-list"),
            ],
        )
        # Check that the extra action links were generated correctly
        self.assertCountEqual(
            field.action_links,
            [
                ("events", "project-events"),
                ("submit-for-review", "project-submit-for-review"),
                ("request-changes", "project-request-changes"),
                ("submit-for-provisioning", "project-submit-for-provisioning"),
            ],
        )

    def test_to_representation(self):
        # Make a project to test with
        consortium = Consortium.objects.create(
            name="Consortium 1",
            description="some description",
            manager=get_user_model().objects.create_user("manager1"),
        )
        project = consortium.projects.create(
            name="Project 1",
            description="some description",
            owner=get_user_model().objects.create_user("owner1"),
        )
        # Make a fake request to give in the context for reversing
        request = APIRequestFactory().get("/projects/")
        # Test that the correct representation is generated
        field = LinksField(
            basename="project",
            related_object_links=[("consortium", "consortium-detail", "consortium_id")],
            related_list_links=[
                ("collaborators", "project-collaborators-list"),
                ("services", "project-services-list"),
            ],
            action_links=[
                ("submit-for-review", "project-submit-for-review"),
                ("request-changes", "project-request-changes"),
                ("submit-for-provisioning", "project-submit-for-provisioning"),
            ],
        )
        # Set the parent to an object just complex enough to provide a context
        field.parent = SimpleNamespace(_context={"request": request}, parent=None)
        self.assertEqual(
            field.to_representation(project),
            {
                "self": "http://testserver/projects/1/",
                "consortium": "http://testserver/consortia/1/",
                "collaborators": "http://testserver/projects/1/collaborators/",
                "services": "http://testserver/projects/1/services/",
                "request-changes": "http://testserver/projects/1/request_changes/",
                "submit-for-provisioning": "http://testserver/projects/1/submit_for_provisioning/",
                "submit-for-review": "http://testserver/projects/1/submit_for_review/",
            },
        )
