from tsunami.helpers import model_event_listener

from tsunami_notify.models import Notification

from .models import Collaborator, Project, Requirement


@model_event_listener(Project, [
    'submitted_for_review',
    'changes_requested',
    'submitted_for_provisioning',
    'completed',
])
def notify_project_collaborators_project_event(event):
    """
    Notify project collaborators of project events.
    """
    # Notify all collaborators of the event except for the user who triggered the event
    collaborators = event.target.collaborators.select_related('user')
    if event.user:
        collaborators = collaborators.exclude(user = event.user)
    for collaborator in collaborators:
        # It is possible that the user may not have an email address defined yet
        if collaborator.user.email:
            Notification.create(
                event,
                collaborator.user.email,
                dict(project_role = Collaborator.Role(collaborator.role).name)
            )


@model_event_listener(Project, ['submitted_for_review'])
def notify_consortium_manager_project_submitted_for_review(event):
    """
    Notify the consortium manager when a project is submitted for review.
    """
    consortium_manager = event.target.consortium.manager
    # If the consortium manager is also the project owner who is submitting
    # the project for review, don't bother sending the notificion
    if (
        event.user and
        event.user != consortium_manager and
        consortium_manager.email
    ):
        Notification.create(
            event,
            consortium_manager.email,
            dict(consortium_manager = True)
        )


@model_event_listener(Requirement, ['provisioned'])
def notify_project_collaborators_requirement_provisioned(event):
    """
    Notify the project collaborators when a requirement is provisioned.
    """
    collaborators = (
        Collaborator.objects
            .filter(project__service__requirement = event.target)
            .select_related('user')
    )
    for collaborator in collaborators:
        # It is possible that the user may not have an email address defined yet
        if collaborator.user.email:
            Notification.create(
                event,
                collaborator.user.email,
                dict(project_role = Collaborator.Role(collaborator.role).name)
            )
