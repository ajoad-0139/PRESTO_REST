import uuid
from django.db import models
from django.utils.text import slugify
from sites.utils import file_upload_path

# theme model for now 
class Theme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=100, blank=True)
    thumbnail = models.CharField(max_length=500, blank=True)
    tokens = models.JSONField(default=dict)
    global_css = models.TextField(blank=True)
    layout = models.JSONField(default=dict)
    pages_template = models.JSONField(default=list)
    blocks = models.JSONField(default=list)
    version = models.CharField(max_length=20, default="1.0.0")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# website model
class Site (models.Model) :
    class Type(models.TextChoices):
        WEBSITE = "website", "Website"
        BLOG = "blog", "Blog"
        LANDING_PAGE = "landing_page", "Landing Page"
        PORTFOLIO = "portfolio", "Portfolio"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=50, choices=Type.choices, default=Type.WEBSITE)
    language = models.CharField(max_length=10, default="en")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_domain = models.CharField(max_length=255, blank=True, null=True, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    theme = models.ForeignKey(Theme, on_delete=models.PROTECT, related_name="websites")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["type"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or str(self.id)[:8]
            slug = base_slug
            counter = 1
            while Site.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# uploaded file path
class UploadedFilePath(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.FileField(upload_to=file_upload_path)

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="uploaded_file_paths")

    def __str__(self):
        return self.url




# page model 
class Page(models.Model) :
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    page_type = models.CharField(max_length=255)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)
    og_title = models.CharField(max_length=255, blank=True)
    og_description = models.TextField(blank=True)

    # flags
    ck_enabled = models.BooleanField(default=False)
    is_dynamic_blog_page = models.BooleanField(default=False)
    has_weather_component = models.BooleanField(default=False)

    content = models.TextField()
    css_file = models.ForeignKey("UploadedFilePath", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    js_file = models.ForeignKey("UploadedFilePath", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    canonical_url = models.TextField(max_length=255, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="pages")

    def __str__(self):
        return self.title


class PageFAQ(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=500)
    answer = models.TextField()
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position"]


# website's page navigation model
class Navigation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=255)
    path = models.CharField(max_length=500)

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="site_navigation")
    page = models.OneToOneField(Page, on_delete=models.PROTECT, related_name="page_navigation" )

    def __str__(self):
        return self.label