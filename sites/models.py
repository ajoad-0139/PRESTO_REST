import uuid
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils.text import slugify
from sites.utils import file_upload_path
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp", "svg")
VIDEO_EXTENSIONS = ("mp4", "webm", "mov", "m4v", "ogv")

video_validator = FileExtensionValidator(allowed_extensions=list(VIDEO_EXTENSIONS))
image_validator = FileExtensionValidator(allowed_extensions=list(IMAGE_EXTENSIONS) + ["ico"])
html_validator = FileExtensionValidator(allowed_extensions=["html", "htm"])
css_validator = FileExtensionValidator(allowed_extensions=["css"])
js_validator = FileExtensionValidator(allowed_extensions=["js"])


# theme model 
class Theme(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    language = models.CharField(max_length=10, default="en")
    thumbnail = models.ImageField(upload_to=file_upload_path, validators=[image_validator])
 
    header = models.FileField(upload_to=file_upload_path, validators=[html_validator])
    footer = models.FileField(upload_to=file_upload_path, validators=[html_validator])
    body = models.FileField(upload_to=file_upload_path, validators=[html_validator])
 
    css_file = models.FileField(upload_to=file_upload_path, validators=[css_validator])
    js_file = models.FileField(upload_to=file_upload_path, null=True, blank=True, validators=[js_validator])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or str(self.id)[:8]
            slug = base_slug
            counter = 1
            while Theme.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name




# website model
class Site (models.Model) :

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=10, default="en")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_domain = models.CharField(max_length=255, blank=True, null=True, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    favicon = models.ImageField(upload_to=file_upload_path, null=True, blank=True, validators=[image_validator])

    meta_description = models.CharField(max_length=160, blank=True)
    og_image = models.FileField(upload_to=file_upload_path, null=True, blank=True, validators=[image_validator])
    no_index = models.BooleanField(default=False)
     
    header = models.FileField(upload_to=file_upload_path, validators=[html_validator])
    footer = models.FileField(upload_to=file_upload_path, validators=[html_validator])
    body = models.FileField(upload_to=file_upload_path, validators=[html_validator])
    
    css_file = models.FileField(upload_to=file_upload_path, validators=[css_validator])
    js_file = models.FileField(upload_to=file_upload_path, null=True, blank=True, validators=[js_validator])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE, related_name="sites")
    theme = models.ForeignKey(Theme, on_delete=models.PROTECT, related_name="sites")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
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





# page model 
class Page(models.Model) :

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    page_type = models.CharField(max_length=255)
    canonical_url = models.TextField(max_length=500, default="")

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    og_title = models.CharField(max_length=95, blank=True)
    og_description = models.CharField(max_length=200, blank=True)
    og_image = models.FileField(upload_to=file_upload_path, null=True, blank=True, validators=[image_validator])
    no_index = models.BooleanField(default=False)

    html_file = models.FileField(upload_to=file_upload_path, null=True, blank=True, validators=[html_validator])
    css_file = models.FileField(upload_to=file_upload_path, null=True, blank=True, validators=[css_validator])
    js_file = models.FileField(upload_to=file_upload_path, null=True, blank=True, validators=[js_validator])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="pages")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["site", "slug"], name="uniq_page_slug_per_site"),
        ]

 
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or str(self.id)[:8]
            slug = base_slug
            counter = 1
            while Page.objects.filter(site=self.site, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title




# image model
class Image(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ImageField(upload_to=file_upload_path, width_field="width", height_field="height")
    width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    size = models.PositiveBigIntegerField(null=True, blank=True, editable=False) 
    alt_text = models.CharField(max_length=255, blank=True)

    theme = models.ForeignKey("Theme", null=True, blank=True, on_delete=models.PROTECT, related_name="image_assets")
    site = models.ForeignKey("Site", null=True, blank=True, on_delete=models.CASCADE, related_name="image_assets")
    page = models.ForeignKey("Page", null=True, blank=True, on_delete=models.CASCADE, related_name="image_assets")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(theme__isnull=False, site__isnull=True, page__isnull=True)
                    | Q(theme__isnull=True, site__isnull=False)
                ),
                name="image_owner_valid",
            ),
        ]

    def clean(self):
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id
        if self.page_id and self.page.site_id != self.site_id:
            raise ValidationError({"page": "Page belongs to a different site."})

    def save(self, *args, **kwargs):
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id
        self.clean()
        if self.file:
            self.size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return self.file.name



# video field
class Video(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=file_upload_path, validators=[video_validator])
    size = models.PositiveBigIntegerField(null=True, blank=True, editable=False)  
    title = models.CharField(max_length=255, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Seconds")
    poster = models.ImageField(upload_to=file_upload_path, null=True, blank=True)  

    theme = models.ForeignKey("Theme", null=True, blank=True, on_delete=models.PROTECT, related_name="video_assets")
    site = models.ForeignKey("Site", null=True, blank=True, on_delete=models.CASCADE, related_name="video_assets")
    page = models.ForeignKey("Page", null=True, blank=True, on_delete=models.CASCADE, related_name="video_assets")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(theme__isnull=False, site__isnull=True, page__isnull=True)
                    | Q(theme__isnull=True, site__isnull=False)
                ),
                name="video_owner_valid",
            ),
        ]

    def clean(self):
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id
        if self.page_id and self.page.site_id != self.site_id:
            raise ValidationError({"page": "Page belongs to a different site."})

    def save(self, *args, **kwargs):
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id
        self.clean()
        if self.file:
            self.size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or self.file.name