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
    bio = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_detective = models.BooleanField(default=False)
    detective_status = models.CharField(
        max_length=20, 
        choices=DETECTIVE_STATUS_CHOICES, 
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Case(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_cases')
    title = models.CharField(max_length=200)
    description = models.TextField()
    case_type = models.CharField(max_length=10, choices=CASE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=CASE_STATUS_CHOICES, default='OPEN')
    
    # Manual location input only - NO Lat/Lon
    location = models.CharField(max_length=255, help_text="City, Street, or Landmark")
    
    date_occurred = models.DateField()
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

class CaseImage(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='case_images/')
    clip_embedding = models.JSONField(null=True, blank=True, help_text="Stores CLIP vector as list")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.case.title}"

class SightingReport(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='sightings')
    reporter_name = models.CharField(max_length=100)
    reporter_contact = models.CharField(max_length=100)
    description = models.TextField()
    sighting_date = models.DateField()
    sighting_location = models.CharField(max_length=255, help_text="Where was it seen?")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sighting for {self.case.title} by {self.reporter_name}"

class DetectiveRequest(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='detective_requests')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    offered_reward = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined')], default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request for {self.case.title}"

class CaseAssignment(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='assignments')
    detective = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'profile__is_detective': True})
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_cases')
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS_CHOICES, default='PENDING')
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.detective.username} -> {self.case.title}"

class InvestigationUpdate(models.Model):
    assignment = models.ForeignKey(CaseAssignment, on_delete=models.CASCADE, related_name='updates')
    notes = models.TextField()
    evidence_photo = models.ImageField(upload_to='evidence/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Update for {self.assignment.case.title}"

class DetectiveAchievement(models.Model):
    detective = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='achievements/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Feedback(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_feedback')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}"

class Blog(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='blog/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
