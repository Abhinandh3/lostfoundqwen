from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """User profile model extending Django's User model."""
    ROLE_CHOICES = [
        ('citizen', 'Citizen'),
        ('detective', 'Detective'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citizen')
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='USA')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Case(models.Model):
    """Model representing a lost or found case."""
    CASE_TYPE_CHOICES = [
        ('lost', 'Lost'),
        ('found', 'Found'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_investigation', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    CATEGORY_CHOICES = [
        ('electronics', 'Electronics'),
        ('jewelry', 'Jewelry'),
        ('documents', 'Documents'),
        ('clothing', 'Clothing'),
        ('pets', 'Pets'),
        ('wallet', 'Wallet'),
        ('keys', 'Keys'),
        ('bag', 'Bag'),
        ('vehicle', 'Vehicle'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    case_type = models.CharField(max_length=10, choices=CASE_TYPE_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='open')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    
    # Location details
    location_name = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Date and time
    incident_date = models.DateField()
    incident_time = models.TimeField(blank=True, null=True)
    
    # Item details
    item_color = models.CharField(max_length=50, blank=True, null=True)
    item_brand = models.CharField(max_length=100, blank=True, null=True)
    item_model = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    distinctive_features = models.TextField(blank=True, null=True)
    
    # Reward
    reward_offered = models.BooleanField(default=False)
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Owner
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cases')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"[{self.get_case_type_display()}] {self.title}"


class CaseImage(models.Model):
    """Model for storing images related to a case."""
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='case_images/')
    caption = models.CharField(max_length=200, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.case.title}"


class SightingReport(models.Model):
    """Model for reporting sightings of lost items or found item matches."""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('investigating', 'Under Investigation'),
    ]
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='sightings')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sightings')
    
    sighting_date = models.DateField()
    sighting_time = models.TimeField(blank=True, null=True)
    location_description = models.TextField()
    sighting_details = models.TextField()
    
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewer_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Sighting for {self.case.title} by {self.reporter.username}"


class DetectiveRequest(models.Model):
    """Model for citizens requesting detective assistance."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
    ]
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='detective_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests_made')
    requested_detective = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='requests_received',
        limit_choices_to={'profile__role': 'detective'}
    )
    
    message = models.TextField(blank=True, null=True)
    proposed_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    response_message = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Request to {self.requested_detective.username} for {self.case.title}"


class CaseAssignment(models.Model):
    """Model for tracking detective assignments to cases."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
    ]
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='assignments')
    detective = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='assigned_cases',
        limit_choices_to={'profile__role': 'detective'}
    )
    assigned_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name='assignments_made',
        null=True
    )
    
    assignment_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    contract_terms = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.detective.username} assigned to {self.case.title}"


class InvestigationUpdate(models.Model):
    """Model for detectives to provide investigation updates."""
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('owner_only', 'Owner Only'),
        ('private', 'Private (Detective & Admin)'),
    ]
    
    UPDATE_TYPE_CHOICES = [
        ('progress', 'Progress Report'),
        ('breakthrough', 'Breakthrough'),
        ('dead_end', 'Dead End'),
        ('interview', 'Interview Conducted'),
        ('evidence', 'New Evidence'),
        ('location_search', 'Location Search'),
        ('other', 'Other'),
    ]
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='investigation_updates')
    detective = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='investigation_updates',
        limit_choices_to={'profile__role': 'detective'}
    )
    
    update_type = models.CharField(max_length=30, choices=UPDATE_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='owner_only')
    
    evidence_photos = models.ImageField(upload_to='evidence/', blank=True, null=True)
    documents = models.FileField(upload_to='investigation_docs/', blank=True, null=True)
    
    location_visited = models.CharField(max_length=200, blank=True, null=True)
    persons_contacted = models.CharField(max_length=200, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Update: {self.title} for {self.case.title}"


class DetectiveAchievement(models.Model):
    """Model for tracking detective achievements and badges."""
    ACHIEVEMENT_TYPE_CHOICES = [
        ('badge', 'Badge'),
        ('certificate', 'Certificate'),
        ('title', 'Title'),
        ('milestone', 'Milestone'),
    ]
    
    CATEGORY_CHOICES = [
        ('cases_solved', 'Cases Solved'),
        ('speed', 'Quick Resolution'),
        ('rating', 'High Rating'),
        ('specialization', 'Specialization'),
        ('community', 'Community Contribution'),
        ('tenure', 'Tenure'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPE_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    
    icon = models.ImageField(upload_to='achievements/', blank=True, null=True)
    points_required = models.IntegerField(default=0)
    cases_required = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DetectiveAchievementAward(models.Model):
    """Model for awarded achievements to detectives."""
    detective = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='awarded_achievements',
        limit_choices_to={'profile__role': 'detective'}
    )
    achievement = models.ForeignKey(DetectiveAchievement, on_delete=models.CASCADE)
    
    awarded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ['detective', 'achievement']

    def __str__(self):
        return f"{self.detective.username} - {self.achievement.name}"


class Feedback(models.Model):
    """Model for user feedback on cases and detectives."""
    RATING_CHOICES = [
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]
    
    FEEDBACK_TYPE_CHOICES = [
        ('detective', 'Detective Feedback'),
        ('case', 'Case Feedback'),
        ('platform', 'Platform Feedback'),
    ]
    
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    
    # For detective feedback
    detective = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='detective_feedback',
        null=True,
        blank=True,
        limit_choices_to={'profile__role': 'detective'}
    )
    
    # For case feedback
    case = models.ForeignKey(
        Case, 
        on_delete=models.CASCADE, 
        related_name='feedback',
        null=True,
        blank=True
    )
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback_given')
    
    rating = models.IntegerField(choices=RATING_CHOICES, blank=True, null=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    comment = models.TextField()
    
    is_anonymous = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    is_verified_purchase = models.BooleanField(default=False)  # For paid detective services
    
    admin_response = models.TextField(blank=True, null=True)
    admin_responded_at = models.DateTimeField(blank=True, null=True)
    
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.detective:
            return f"Feedback for {self.detective.username} by {self.author.username}"
        elif self.case:
            return f"Feedback for case {self.case.title} by {self.author.username}"
        else:
            return f"Platform feedback by {self.author.username}"


class Blog(models.Model):
    """Model for blog posts about lost and found tips, success stories, etc."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    CATEGORY_CHOICES = [
        ('tips', 'Tips & Advice'),
        ('success_story', 'Success Story'),
        ('news', 'News & Updates'),
        ('safety', 'Safety Tips'),
        ('community', 'Community'),
        ('tutorial', 'Tutorial'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    content = models.TextField()
    excerpt = models.TextField(blank=True, null=True)
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='tips')
    
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    
    tags = models.CharField(max_length=500, blank=True, null=True, help_text="Comma-separated tags")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    views_count = models.IntegerField(default=0)
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    
    seo_title = models.CharField(max_length=200, blank=True, null=True)
    seo_description = models.TextField(blank=True, null=True)
    seo_keywords = models.CharField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_at', '-created_at']
