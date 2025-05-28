from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class SystemVersion(models.Model):
    """Tracks system version numbers and release information"""
    MAJOR = 'major'
    MINOR = 'minor'
    PATCH = 'patch'
    VERSION_TYPE_CHOICES = [
        (MAJOR, 'Major Release'),
        (MINOR, 'Minor Release'),
        (PATCH, 'Patch/Bugfix'),
    ]
    
    version_number = models.CharField(max_length=20, unique=True, help_text="Format: x.y.z (e.g., 1.0.0)")
    version_name = models.CharField(max_length=100, blank=True, help_text="Optional name for this version")
    version_type = models.CharField(max_length=10, choices=VERSION_TYPE_CHOICES, default=PATCH)
    release_date = models.DateField()
    is_current = models.BooleanField(default=False, help_text="Is this the current active version?")
    release_notes = models.TextField(blank=True)
    developer = models.CharField(max_length=100, default="TTU IT Department")
    
    def __str__(self):
        if self.version_name:
            return f"v{self.version_number} - {self.version_name}"
        return f"v{self.version_number}"
    
    def save(self, *args, **kwargs):
        # If this version is marked as current, unmark all others
        if self.is_current:
            SystemVersion.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-release_date']
        verbose_name = "System Version"
        verbose_name_plural = "System Versions"


class DocumentationSection(models.Model):
    """Main documentation sections"""
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, editable=False)
    order = models.PositiveSmallIntegerField(default=0, help_text="Display order of this section")
    content = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Documentation Section"
        verbose_name_plural = "Documentation Sections"


class SubSection(models.Model):
    """Sub-sections within documentation sections"""
    section = models.ForeignKey(DocumentationSection, on_delete=models.CASCADE, related_name='subsections')
    title = models.CharField(max_length=100)
    slug = models.SlugField(editable=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    content = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.section.title} > {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['section__order', 'order']
        unique_together = ('section', 'slug')
        verbose_name = "Documentation Subsection"
        verbose_name_plural = "Documentation Subsections"


class DocumentationItem(models.Model):
    """Individual documentation list items"""
    subsection = models.ForeignKey(SubSection, on_delete=models.CASCADE, related_name='items')
    text = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)
    
    def __str__(self):
        return self.text[:50]
    
    class Meta:
        ordering = ['subsection__section__order', 'subsection__order', 'order']
        verbose_name = "Documentation Item"
        verbose_name_plural = "Documentation Items"


class ContactInfo(models.Model):
    """Contact information for system support"""
    title = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    additional_info = models.TextField(blank=True)
    section = models.ForeignKey(DocumentationSection, on_delete=models.CASCADE, related_name='contacts', null=True)
    order = models.PositiveSmallIntegerField(default=0)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['order']
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"


class AnonymousFeedback(models.Model):
    """Model for storing anonymous user feedback"""
    CATEGORY_CHOICES = [
        ('general', 'General Feedback'),
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('usability', 'Usability Issue'),
        ('experience', 'User Experience'),
    ]
    
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]
    
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    message = models.TextField()
    rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    submission_date = models.DateTimeField(default=timezone.now)
    is_addressed = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    page_url = models.CharField(max_length=255, blank=True, help_text="URL where feedback was submitted from")
    
    class Meta:
        verbose_name = "Anonymous Feedback"
        verbose_name_plural = "Anonymous Feedback"
        ordering = ['-submission_date']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.submission_date.strftime('%Y-%m-%d %H:%M')}"
