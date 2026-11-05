import os
import uuid
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils.text import slugify
from sites.utils import file_upload_path
from django.core.exceptions import ValidationError

IMAGE_EXTENSIONS = ("jpg", "jpeg", "png",  "gif", "webp", "svg")

#meta 
class Meta(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)
    og_title = models.CharField(max_length=255, blank=True)
    og_description = models.TextField(blank=True)
    og_image = models.OneToOneField("UploadedFilePath", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

# theme model for now 
class Theme(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    favicon = models.OneToOneField("UploadedFilePath", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    thumbnail = models.OneToOneField("UploadedFilePath", on_delete=models.PROTECT, related_name="+")
    is_active = models.BooleanField(default=True)

    language = models.CharField(max_length=10, default="en")

    meta = models.OneToOneField("Meta", null=True, blank=True, on_delete=models.PROTECT, related_name="theme")

    header = models.OneToOneField("UploadedFilePath", on_delete=models.PROTECT, related_name="+")
    footer = models.OneToOneField("UploadedFilePath", on_delete=models.PROTECT, related_name="+")
    body = models.OneToOneField("UploadedFilePath", on_delete=models.PROTECT, related_name="+")

    css_file = models.OneToOneField("UploadedFilePath", on_delete=models.PROTECT, related_name="+")
    js_file = models.OneToOneField("UploadedFilePath", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def assets(self):
        special = [pk for pk in (self.thumbnail_id, self.favicon_id) if pk]
        return (
            self.theme_assets
            .filter(extension__in=IMAGE_EXTENSIONS)
            .exclude(pk__in=special)
        )

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

    owner = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE, related_name="sites")
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
 
    extension = models.CharField(max_length=10, blank=True, db_index=True, editable=False)
 
    theme = models.ForeignKey("Theme", null=True, blank=True, on_delete=models.CASCADE, related_name="theme_assets")
    site = models.ForeignKey("Site", null=True, blank=True, on_delete=models.CASCADE, related_name="uploaded_file_paths")
    page = models.ForeignKey("Page", null=True, blank=True, on_delete=models.CASCADE, related_name="page_assets")
 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~Q(theme__isnull=False, site__isnull=False)   
                    & ~Q(theme__isnull=False, page__isnull=False)   
                    & (Q(page__isnull=True) | Q(site__isnull=False))  
                ),
                name="file_owner_valid",
            ),
        ]
 
    def clean(self):
        if self.page_id and self.page.site_id != self.site_id:
            raise ValidationError({"page": "Page belongs to a different site."})
 
    def save(self, *args, **kwargs):
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id      
        self.clean()
        if self.url:
            self.extension = os.path.splitext(self.url.name)[1].lower().lstrip(".")
        super().save(*args, **kwargs)
 
    def __str__(self):
        return self.url.name


# page model 
class Page(models.Model) :
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)

    slug = models.SlugField(max_length=255, blank=True)

    page_type = models.CharField(max_length=255)
    meta = models.OneToOneField("meta", null=True, blank=True, on_delete=models.SET_NULL, related_name="page")

    html_file = models.OneToOneField("UploadedFilePath", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    css_file = models.OneToOneField("UploadedFilePath", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    js_file = models.OneToOneField("UploadedFilePath", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")


    canonical_url = models.TextField(max_length=500, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="pages")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["site", "slug"], name="uniq_page_slug_per_site"),
        ]

    def assets(self):
        og_image_id = self.meta.og_image_id if self.meta_id else None
        return (
            self.page_assets
            .filter(extension__in=IMAGE_EXTENSIONS)
            .exclude(pk=og_image_id)
        )
    
    def clean(self):
        for field in ("css_file", "js_file"):
            f = getattr(self, field)
            if f and f.site_id != self.site_id:
                raise ValidationError({field: "File belongs to a different site."})
 
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or str(self.id)[:8]
            slug = base_slug
            counter = 1
            while Page.objects.filter(site=self.site, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class PageFAQ(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.CharField(max_length=500)
    answer = models.TextField()
    position = models.PositiveSmallIntegerField(default=0)

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="theme_faqs")
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="faqs")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["position"]


# website's page navigation model
class Navigation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=255)
    path = models.CharField(max_length=500)
    position = models.PositiveSmallIntegerField(default=0)

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="site_navigation")
    page = models.OneToOneField(Page, on_delete=models.PROTECT, related_name="page_navigation" )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["site", "path"], name="uniq_nav_path_per_site_location"
            ),
        ]

    def __str__(self):
        return self.label