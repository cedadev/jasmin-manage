from django.contrib.auth import get_user_model

from tsunami.helpers import model_event_listener

from tsunami_notify.models import Notification

from .models import Collaborator, Invitation, Project, Requirement, Comment

import json 

import requests

import os


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


@model_event_listener(Project, ['submitted_for_provisioning'])
def notify_slack_project_submitted_for_provisioning(event):
    """
    Notify staff via slack channel when a project is submitted for provisioning.
    """
    # Only send a notification if a webhook is given
    if "SLACK_WEBHOOK_URL" in os.environ:
        # Get the comments on the project
        print(os.environ.get('SLACK_WEBHOOK_URL'), os.environ.get('SERVICE_REQUEST_URL'))
        comments = (
            Comment.objects
            .filter(project = event.target.id)
            .select_related('project')
        )
        # Get the requirements associated with the project
        requirements = (
            # Requirements with status=40 are awaiting provisioning
            Requirement.objects
            .filter(status="40", service__project=event.target.id)
            .order_by('service_id')
        )
        # For each requirement list the service, resource and amount requested
        service_str =""
        for j in requirements:
            service_str = service_str+" \n *Service:      * <"+os.environ.get('SERVICE_REQUEST_URL')+str(j.service.id)+"|"+j.service.name+">\n *Resource:  * "+j.resource.name+"\n *Amount:    * "+str(j.amount)+"\n"
        # Compose the message to send using slack blocks
        message = {
            "text": "New requirement[s] submitted for provisioning.",
            "blocks": [
		            {
			            "type": "header",
			            "text": {
				            "type": "plain_text",
				            "text": "New requirement[s] submitted for provisioning for the `"+event.target.name+"` project in the `"+str(event.target.consortium)+"` consortium.",
			            }
		            },
		            {
			            "type": "section",
			            "fields": [
				            {
					            "type": "mrkdwn",
					            "text": ">*Comment:*\n>*"+comments[0].created_at.strftime('%d %b %y %H:%M')+"* ' _" +comments[0].content+"_ '"
				            }
			            ]
		            },
		            {
			            "type": "section",
			            "fields": [
                            {
                                "type":"mrkdwn",
                                "text": service_str
                            },
			            ]
		            }
	            ]
        }
        response = requests.post(os.environ.get('SLACK_WEBHOOK_URL'), json.dumps(message))
        if response.status_code != 200:
            raise ValueError(
                'Request to slack returned an error %s, the response is:\n%s'
                % (response.status_code, response.text)
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


@model_event_listener(Collaborator, ['created'])
def notify_project_collaborators_new_collaborator(event):
    """
    Notify the collaborators when a new collaborator joins a project.
    """
    collaborators = event.target.project.collaborators.select_related('user')
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


@model_event_listener(Collaborator, ['deleted'])
def notify_project_collaborator_removed(event):
    """
    When a collaborator is removed from a project, notify them.
    """
    # The collaborator record, i.e. event.target, will no longer exist
    # But the last known state is recorded in the event data, so we can get the user from that
    user = get_user_model().objects.filter(pk = event.data["user"]).first()
    # If we found a user and they have an email set, notify them, unless they
    # removed themselves
    if user and user.email and user != event.user:
        # Get the project from the event data and store the project name in the context,
        # since we can't access it in the template using target.project.name
        project = Project.objects.get(pk = event.data["project"])
        Notification.create(
            event,
            user.email,
            dict(project_name = project.name)
        )


@model_event_listener(Invitation, ['created'])
def notify_invitee(event):
    """
    Notify the invitee when an invitation is created.
    """
    Notification.create(event, event.target.email)
