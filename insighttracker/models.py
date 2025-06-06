from django.db import models
import uuid
from django.utils import timezone
from users.models import User
from children.models import Child

class InsightTracker(models.Model):
    """
    Tracks analytics and behavioral insights for Parents (Users) and Children.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Optional link to a parent user (if tracking parent insights)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='insight_tracker',
        null=True,
        blank=True
    )

    # Optional link to a child user (if tracking child insights)
    child = models.OneToOneField(
        Child,
        on_delete=models.CASCADE,
        related_name='insight_tracker',
        null=True,
        blank=True
    )

    # Common metrics (can apply to either user or child)
    total_tasks_created = models.PositiveIntegerField(default=0)
    total_tasks_completed = models.PositiveIntegerField(default=0)
    total_tasks_missed = models.PositiveIntegerField(default=0)
    total_rewards_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    average_completion_time_seconds = models.FloatField(null=True, blank=True)

    # Temporal tracking (e.g., weekly stats)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Insight for Parent: {self.user.full_name}"
        elif self.child:
            return f"Insight for Child: {self.child.username}"
        return "Unlinked Insight Tracker"
