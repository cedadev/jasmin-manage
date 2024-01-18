import random

from django.contrib.auth import get_user_model
from django.test import TestCase

from ...models import Category, Collaborator, Consortium, Project, Requirement, Resource

from ..utils import AssertValidationErrorsMixin


class ProjectModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the project model.
    """

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        Project.objects.create(
            name="Project 1",
            consortium=Consortium.objects.create(
                name="Consortium 1",
                description="some description",
                manager=UserModel.objects.create_user("manager1"),
            ),
            owner=UserModel.objects.create_user("user1"),
        )

    def test_create_makes_owner(self):
        # Test that creating the project created a collaborator instance for the owner
        project = Project.objects.first()
        collaborators = project.collaborators.all()
        self.assertEqual(collaborators.count(), 1)
        self.assertEqual(collaborators[0].user.username, "user1")
        self.assertEqual(collaborators[0].role, Collaborator.Role.OWNER)

    def test_annotate_summary(self):
        """
        Test that annotating a project query with summary information works as expected.
        """
        UserModel = get_user_model()

        # Keep track of the expected results as we create stuff
        expected = {}

        # Get the consortium to use
        consortium = Consortium.objects.first()
        # Create a category to use
        category = Category.objects.create(
            name="Category 1", description="Some description"
        )
        # Create a resource to use
        resource = Resource.objects.create(
            name="Resource 1", description="Some description"
        )

        # Create a user to be the current user
        current_user = UserModel.objects.create_user("current_user")

        # Create 10 projects without any collaborators
        projects = []
        for i in range(10):
            project = Project(
                name=f"Summary Project {i}",
                description="Some description",
                consortium=consortium,
            )
            project.save()
            projects.append(project)
            expected.setdefault(
                project.pk,
                dict(
                    num_services=0,
                    num_requirements=0,
                    num_collaborators=0,
                    current_user_role=None,
                ),
            )

        # Create 40 services spread randomly across the projects
        services = []
        for i in range(40):
            project = random.choice(projects)
            services.append(
                category.services.create(name=f"service{i}", project=project)
            )
            expected[project.pk]["num_services"] += 1

        # Create 100 requirements spread randomly across services
        for i in range(100):
            service = random.choice(services)
            service.requirements.create(resource=resource, amount=100)
            expected[service.project.pk]["num_requirements"] += 1

        # Choose 6 random projects to add the current_user as a collaborator
        for project in random.sample(projects, 6):
            # Pick which role to give them at random
            role = random.choice(list(Collaborator.Role))
            project.collaborators.create(user=current_user, role=role)
            expected[project.pk]["num_collaborators"] += 1
            expected[project.pk]["current_user_role"] = role

        # For each project, add between 0 and 3 other collaborators
        for i, project in enumerate(projects):
            num_collaborators = random.randint(0, 3)
            for j in range(num_collaborators):
                project.collaborators.create(
                    user=UserModel.objects.create_user(f"summary{i}{j}"),
                    role=random.choice(list(Collaborator.Role)),
                )
            expected[project.pk]["num_collaborators"] += num_collaborators

        # Compare each project to the expected values
        # We do this for both an annotated and un-annotated query to test both methods of obtaining the information
        queryset = Project.objects.filter(name__startswith="Summary")
        for qs in [queryset.all(), queryset.annotate_summary(current_user)]:
            for project in qs:
                self.assertEqual(
                    project.get_num_services(), expected[project.pk]["num_services"]
                )
                self.assertEqual(
                    project.get_num_requirements(),
                    expected[project.pk]["num_requirements"],
                )
                self.assertEqual(
                    project.get_num_collaborators(),
                    expected[project.pk]["num_collaborators"],
                )
                self.assertEqual(
                    project.get_current_user_role(current_user),
                    expected[project.pk]["current_user_role"],
                )

    def test_name_unique(self):
        self.assertTrue(Project._meta.get_field("name").unique)

    def test_to_string(self):
        project = Project.objects.first()
        self.assertEqual(str(project), "Project 1")

    def test_natural_key(self):
        project = Project.objects.first()
        self.assertEqual(project.natural_key(), ("Project 1",))

    def test_get_by_natural_key(self):
        project = Project.objects.get_by_natural_key("Project 1")
        self.assertEqual(project.pk, 1)

    def test_get_event_type_editable_requirements_rejected(self):
        """
        Tests that get_event_type reports "changes_requested" when a project
        transitions to the EDITABLE status with rejected requirements.
        """
        project = Project.objects.first()
        service = project.services.create(
            category=Category.objects.create(
                name="Category 1", description="Description."
            ),
            name="service1",
        )
        service.requirements.create(
            resource=Resource.objects.create(name="Resource 1"),
            amount=1000,
            status=Requirement.Status.REJECTED,
        )
        diff = dict(status=Project.Status.EDITABLE)
        event_type = project.get_event_type(diff)
        self.assertEqual(event_type, "jasmin_manage.project.changes_requested")

    def test_get_event_type_editable_requirements_awaiting_provisioning(self):
        """
        Tests that get_event_type reports "submitted_for_provisioning" when a project
        transitions to the EDITABLE status with requirements awaiting provisioning.
        """
        project = Project.objects.first()
        service = project.services.create(
            category=Category.objects.create(
                name="Category 1", description="Description."
            ),
            name="service1",
        )
        service.requirements.create(
            resource=Resource.objects.create(name="Resource 1"),
            amount=1000,
            status=Requirement.Status.AWAITING_PROVISIONING,
        )
        diff = dict(status=Project.Status.EDITABLE)
        event_type = project.get_event_type(diff)
        self.assertEqual(event_type, "jasmin_manage.project.submitted_for_provisioning")

    def test_get_event_type_editable(self):
        """
        Tests that, other than the two circumstances above, get_event_type defers to the
        default event type when a project moves to the EDITABLE status.
        """
        project = Project.objects.first()
        diff = dict(status=Project.Status.EDITABLE)
        self.assertIsNone(project.get_event_type(diff))
        service = project.services.create(
            category=Category.objects.create(
                name="Category 1", description="Description."
            ),
            name="service1",
        )
        service.requirements.create(
            resource=Resource.objects.create(name="Resource 1"),
            amount=1000,
            status=Requirement.Status.APPROVED,
        )
        service.requirements.create(
            resource=Resource.objects.create(name="Resource 2"),
            amount=1000,
            status=Requirement.Status.PROVISIONED,
        )
        self.assertIsNone(project.get_event_type(diff))

    def test_get_event_type_under_review_requirements_requested(self):
        """
        Tests that get_event_type reports "submitted_for_review" when a project
        transitions to the UNDER_REVIEW status with requested requirements.
        """
        project = Project.objects.first()
        service = project.services.create(
            category=Category.objects.create(
                name="Category 1", description="Description."
            ),
            name="service1",
        )
        service.requirements.create(
            resource=Resource.objects.create(name="Resource 1"),
            amount=1000,
            status=Requirement.Status.REQUESTED,
        )
        diff = dict(status=Project.Status.UNDER_REVIEW)
        event_type = project.get_event_type(diff)
        self.assertEqual(event_type, "jasmin_manage.project.submitted_for_review")

    def test_get_event_type_under_review(self):
        """
        Tests that, other than the circumstances above, get_event_type defers to the default
        event type when a project moves to the UNDER_REVIEW status.
        """
        project = Project.objects.first()
        diff = dict(status=Project.Status.UNDER_REVIEW)
        self.assertIsNone(project.get_event_type(diff))
        service = project.services.create(
            category=Category.objects.create(
                name="Category 1", description="Description."
            ),
            name="service1",
        )
        service.requirements.create(
            resource=Resource.objects.create(name="Resource 1"),
            amount=1000,
            status=Requirement.Status.APPROVED,
        )
        service.requirements.create(
            resource=Resource.objects.create(name="Resource 2"),
            amount=1000,
            status=Requirement.Status.PROVISIONED,
        )
        self.assertIsNone(project.get_event_type(diff))

    def test_get_event_type_completed(self):
        """
        Tests that get_event_type reports "completed" when a project transitions into
        the COMPLETED state.
        """
        project = Project.objects.first()
        diff = dict(status=Project.Status.COMPLETED)
        event_type = project.get_event_type(diff)
        self.assertEqual(event_type, "jasmin_manage.project.completed")

    def test_get_event_type_no_status(self):
        project = Project.objects.first()
        # If status is not in diff, the event type should be null
        diff = dict(name="New project name")
        self.assertIsNone(project.get_event_type(diff))

    def test_get_event_aggregates(self):
        project = Project.objects.first()
        self.assertEqual(project.get_event_aggregates(), (project.consortium,))
