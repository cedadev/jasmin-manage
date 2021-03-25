import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .collaborator import Collaborator
from .project import Project


def default_code():
    """
    Produce a new default code.
    """
    return uuid.uuid4().hex


class Invitation(models.Model):
    """
    Represents an invitation to collaborate on a project.
    """
    class Meta:
        ordering = ('-created_at', )

    #: The project that the user is invited to
    project = models.ForeignKey(
        Project,
        models.CASCADE,
        related_name = 'invitations',
        related_query_name = 'invitation'
    )
    #: The email address for the invitation
    email = models.EmailField()
    #: The code for the invitation
    code = models.CharField(max_length = 32, default = default_code)
    #: The time at which the invitation was created
    created_at = models.DateTimeField(auto_now_add = True)

    def clean(self):
        super().clean()
        # We only have extra validation to do if the project and email are set
        if not self.project or not self.email:
            return
        # Check if there is already a collaborator record for a user with the
        # same email address as the invitation
        collaborator = (
            self.project.collaborators
                .filter(user__email__iexact = self.email)
                .select_related('user')
                .first()
        )
        # If there is, then they do not need to be invited
        if collaborator:
            username = collaborator.user.get_full_name() or collaborator.user.username
            message = 'User with this email address is already a project collaborator ({}).'
            raise ValidationError({ 'email': message.format(username) })
        # Check if there is an invite for the project with the same email address
        # We can't use unique_together for this because we want the match to be case-insensitive
        invitations = self.project.invitations.filter(email__iexact = self.email)
        if not self._state.adding:
            invitations = invitations.exclude(pk = self.pk)
        if invitations.exists():
            message = 'Email address already has an invitation for this project.'
            raise ValidationError({ 'email': message })
