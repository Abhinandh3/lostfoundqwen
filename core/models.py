from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Choices
CASE_STATUS_CHOICES = [
    ('OPEN', 'Open'),
    ('INVESTIGATING', 'Investigating'),
    ('FOUND', 'Found'),
    ('CLOSED', 'Closed'),
]

CASE_TYPE_CHOICES = [
    ('LOST', 'Lost Item/Pet'),
    ('FOUND', 'Found Item/Pet'),
]

DETECTIVE_STATUS_CHOICES = [
    ('PENDING', 'Pending Approval'),
    ('ACTIVE', 'Active'),
    ('SUSPENDED', 'Suspended'),
]

ASSIGNMENT_STATUS_CHOICES = [
    ('PENDING', 'Pending Acceptance'),
    ('ACCEPTED', 'Accepted'),
    ('COMPLETED', 'Completed'),
    ('REJECTED', 'Rejected'),
]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    is_detective = models.BooleanField(default=False)
    detective_status = models.CharField(
        max_length=20, 
        choices=DETECTIVE_STATUS_CHOICES, 
        default='PENDING',
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Case(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_cases')
    title = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    case_type = models.CharField(max_length=10, choices=CASE_TYPE_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=20, choices=CASE_STATUS_CHOICES, default='OPEN', null=True, blank=True)
    
    # Manual location input only - NO Lat/Lon
    location = models.CharField(max_length=255, help_text="City, Street, or Landmark", null=True, blank=True)
    
    date_occurred = models.DateField(default=timezone.now, null=True, blank=True)
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.status})"

class CaseImage(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='case_images/', null=True, blank=True)
    clip_embedding = models.JSONField(null=True, blank=True, help_text="Stores CLIP vector as list")
    uploaded_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return f"Image for {self.case.title if self.case else 'Unknown'}"

class SightingReport(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='sightings')
    reporter_name = models.CharField(max_length=100, null=True, blank=True)
    reporter_contact = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    sighting_date = models.DateField(default=timezone.now, null=True, blank=True)
    sighting_location = models.CharField(max_length=255, help_text="Where was it seen?", null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return f"Sighting for {self.case.title if self.case else 'Unknown'} by {self.reporter_name or 'Anonymous'}"

class DetectiveRequest(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='detective_requests')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(null=True, blank=True)
    offered_reward = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined')], default='PENDING', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return f"Request for {self.case.title if self.case else 'Unknown'}"

class CaseAssignment(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='assignments')
    detective = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'profile__is_detective': True})
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_cases')
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS_CHOICES, default='PENDING', null=True, blank=True)
    assigned_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.detective.username} -> {self.case.title if self.case else 'Unknown'}"

class InvestigationUpdate(models.Model):
    assignment = models.ForeignKey(CaseAssignment, on_delete=models.CASCADE, related_name='updates')
    notes = models.TextField(null=True, blank=True)
    evidence_photo = models.ImageField(upload_to='evidence/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return f"Update for {self.assignment.case.title if self.assignment and self.assignment.case else 'Unknown'}"

class DetectiveAchievement(models.Model):
    detective = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='achievements/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return self.title or 'Untitled Achievement'

class Feedback(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_feedback', null=True, blank=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    admin_reply = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return f"Feedback from {self.sender.username}"

class Blog(models.Model):
    title = models.CharField(max_length=200, null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='blog/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return self.title or 'Untitled Blog'