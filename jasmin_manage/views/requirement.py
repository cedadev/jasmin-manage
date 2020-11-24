from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import SAFE_METHODS
from rest_framework.decorators import action
from rest_framework.response import Response

from ..exceptions import Conflict
from ..models import Project, Requirement
from ..permissions import RequirementPermissions
from ..serializers import RequirementSerializer


# Requirements can only be listed and created via a service
class RequirementViewSet(mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """
    View set for the resource model.
    """
    permission_classes = [RequirementPermissions]

    queryset = Requirement.objects.all()
    serializer_class = RequirementSerializer

    def _check_editable(self, requirement):
        """
        If the requirement is not editable, raise a suitable exception.
        """
        # The project must be in the editable state
        if requirement.service.project.status != Project.Status.EDITABLE:
            raise Conflict('Project is not currently editable.', 'invalid_status')
        # Once a requirement is approved, it cannot be modified
        if requirement.status >= Requirement.Status.APPROVED:
            raise Conflict('Approved requirements cannot be modified.', 'invalid_status')

    def perform_update(self, serializer):
        self._check_editable(serializer.instance)
        # Check if the validated data has anything in - if not, don't apply the update
        if not serializer.validated_data:
            return
        # Updating a requirement causes it to go back into the requested state
        serializer.save(status = Requirement.Status.REQUESTED)

    def perform_destroy(self, instance):
        self._check_editable(instance)
        instance.delete()

    def _check_under_review(self, requirement):
        """
        If the requirement is not in a reviewable status, raise a suitable exception.
        """
        # The project must be in the under review state
        if requirement.service.project.status != Project.Status.UNDER_REVIEW:
            raise Conflict('Project is not currently under review.', 'invalid_status')
        # Allow requirements to move between requested/approved/rejected
        if requirement.status > Requirement.Status.APPROVED:
            raise Conflict(
                'Requirements that have been submitted for provisioning cannot be modified.',
                'invalid_status'
            )

    @action(detail = True, methods = ['POST'], serializer_class = serializers.Serializer)
    def approve(self, request, pk = None):
        """
        Approve the requirement.
        """
        requirement = self.get_object()
        self._check_under_review(requirement)
        # If the requirement is already approved, we can skip all the following checks
        if requirement.status != Requirement.Status.APPROVED:
            # The sum of all approved requirements must always stay under the consortium quota
            # Note that this does NOT prevent us making the total of the quotas greater than the total
            # available amount of a resource, but it does make sure the overallocation is done in a
            # controlled and fair way where consortium managers have to think about their quotas
            consortium = requirement.service.project.consortium
            quota = consortium.quotas.filter(resource = requirement.resource).annotate_usage().first()
            if quota:
                total_allocated = (
                    quota.approved_total +
                    quota.awaiting_provisioning_total +
                    quota.provisioned_total
                )
                quota_amount = quota.amount
            else:
                total_allocated = 0
                quota_amount = 0
            if total_allocated + requirement.amount > quota_amount:
                raise Conflict(
                    'Cannot approve requirement as it would exceed the consortium quota.',
                    'quota_exceeded'
                )
            # Move the requirement into the approved state
            requirement.status = Requirement.Status.APPROVED
            requirement.save()
        context = self.get_serializer_context()
        return Response(RequirementSerializer(requirement, context = context).data)

    @action(detail = True, methods = ['POST'], serializer_class = serializers.Serializer)
    def reject(self, request, pk = None):
        """
        Reject the requirement.
        """
        requirement = self.get_object()
        self._check_under_review(requirement)
        # Move the requirement into the rejected state if required
        if requirement.status != Requirement.Status.REJECTED:
            requirement.status = Requirement.Status.REJECTED
            requirement.save()
        context = self.get_serializer_context()
        return Response(RequirementSerializer(requirement, context = context).data)
