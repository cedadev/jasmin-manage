from django.core.exceptions import ValidationError
from django.db import models

from .consortium import Consortium
from .tag import Tag


class ProjectManager(models.Manager):
    """
    Manager for the project model.
    """

    def get_by_natural_key(self, name):
        return self.get(name=name)


class ProjectQuerySet(models.QuerySet):
    """
    Queryset for the project model.
    """

    def create(self, *, owner, **kwargs):
        from .collaborator import Collaborator

        project = super().create(**kwargs)
        # Make a collaborator object for the given owner
        project.collaborators.create(user=owner, role=Collaborator.Role.OWNER)
        return project

    def annotate_summary(self, current_user):
        """
        Annotates the query with summary information for each project.
        """
        # Import collaborator here to avoid circular dependencies
        from .collaborator import Collaborator

        return self.annotate(
            num_collaborators=models.Count("collaborator", distinct=True),
            num_services=models.Count("service", distinct=True),
            num_tags=models.Count("tags", distinct=True),
            num_requirements=models.Count("service__requirement", distinct=True),
            current_user_role=models.Subquery(
                Collaborator.objects.filter(
                    project=models.OuterRef("pk"), user=current_user
                ).values("role")
            ),
        )


class Project(models.Model):
    """
    Represents a project within a consortium.
    """

    class Meta:
        ordering = ("name",)

    class Status(models.IntegerChoices):
        """
        Represents the status of a project.

        The statuses are ordered as they represent a progression.
        """

        EDITABLE = 10
        UNDER_REVIEW = 20
        COMPLETED = 30

    objects = ProjectManager.from_queryset(ProjectQuerySet)()


    name = models.CharField(max_length=30, unique=True)
    description = models.TextField(help_text="Can contain markdown syntax.")
    status = models.PositiveSmallIntegerField(
        choices=Status.choices, default=Status.EDITABLE
    )
    consortium = models.ForeignKey(
        Consortium,
        models.CASCADE,
        related_name="projects",
        related_query_name="project",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(
        Tag, related_name="project", related_query_name="project", blank=True
    )


    def get_num_services(self):
        if hasattr(self, "num_services"):
            # Use the value from the object if present (e.g. from an annotation)
            return self.num_services
        else:
            # Otherwise calculate it on the fly
            return self.services.count()

    def get_num_requirements(self):
        if hasattr(self, "num_requirements"):
            # Use the value from the object if present (e.g. from an annotation)
            return self.num_requirements
        else:
            # Otherwise calculate it on the fly using a single query
            return (
                self.services.annotate(
                    service_requirement_count=models.Count("requirement", distinct=True)
                )
                .aggregate(requirement_count=models.Sum("service_requirement_count"))
                .get("requirement_count")
                or 0
            )

    def get_num_collaborators(self):
        if hasattr(self, "num_collaborators"):
            # Use the value from the object if present (e.g. from an annotation)
            return self.num_collaborators
        else:
            # Otherwise calculate it on the fly
            return self.collaborators.count()

    def get_current_user_role(self, current_user):
        if hasattr(self, "current_user_role"):
            return self.current_user_role
        else:
            # Otherwise calculate it on the fly
            collaborator = self.collaborators.filter(user=current_user).first()
            return getattr(collaborator, "role", None)

    def get_event_type(self, diff):
        # If the status is not in the diff, just use the default
        if "status" not in diff:
            return
        # If the status is in the diff, we want to use a custom event type that reflects
        # the action taking place
        status = self.Status(diff["status"])
        # To do this, we may need to check the requirements for the project
        from .requirement import Requirement

        requirements = Requirement.objects.filter(service__project=self)
        if status == self.Status.EDITABLE:
            if requirements.filter(status=Requirement.Status.REJECTED).exists():
                # If there are rejected requirements it is a request for changes
                event_type = "changes_requested"
            elif requirements.filter(
                status=Requirement.Status.AWAITING_PROVISIONING
            ).exists():
                # If there are requirements awaiting provisioning, then the project
                # is being submitted for provisioning
                event_type = "submitted_for_provisioning"
            else:
                # If there are no requirements in either status, use the default event type
                return None
        elif status == self.Status.UNDER_REVIEW:
            if requirements.filter(status=Requirement.Status.REQUESTED).exists():
                # If there are requested requirements, then the project is being
                # submitted for review
                event_type = "submitted_for_review"
            else:
                # If not, then use the default event type
                return None
        else:
            # For any other status, just use the status name
            event_type = status.name.lower()
        return "{}.{}".format(self._meta.label_lower, event_type)

    def get_event_aggregates(self):
        # Aggregate project events over the consortium
        return (self.consortium,)

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name
