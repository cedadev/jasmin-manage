from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...models import Invitation


class Command(BaseCommand):
    """
    Prune invitations that are more than a week old.
    """

    help = "Prunes invitations that are more than a week old."

    def handle(self, *args, **options):
        # Get the datetime for one week ago
        one_week_ago = timezone.now() - timedelta(days=7)
        # Delete invitations one at a time so that the tsunami events are recorded
        num_pruned = 0
        for invitation in Invitation.objects.filter(created_at__lt=one_week_ago):
            invitation.delete()
            num_pruned += 1
        self.stdout.write(
            self.style.SUCCESS("{} invitation(s) pruned.".format(num_pruned))
        )
