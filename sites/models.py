import uuid
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils.text import slugify
from sites.utils import file_upload_path
from django.core.exceptions import ValidationError


# theme model
class Theme(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(blank=True, help_text="Leave blank to generate it from the name.")
    description = models.TextField(blank=True, max_length=1000)
    is_active = models.BooleanField(default=True, help_text="Only active themes should be offered when creating a new site.")
    language = models.CharField(max_length=10, default="en", help_text="Language code, e.g. en, bn, fr.")
    thumbnail = models.ImageField(upload_to=file_upload_path)

    header = models.FileField(upload_to=file_upload_path)
    footer = models.FileField(upload_to=file_upload_path)
    body = models.FileField(upload_to=file_upload_path, help_text="HTML file for the main page layout.")

    css_file = models.FileField(upload_to=file_upload_path)
    js_file = models.FileField(upload_to=file_upload_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="themes")

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.name) or str(self.id)[:8]
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# website model
class Site(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=10, default="en", help_text="Language code, e.g. en, bn, fr.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, help_text="Draft: work in progress. Published: live. Archived: retired.")
    published_domain = models.CharField(max_length=255, blank=True, null=True, unique=True, help_text="Custom domain the site is served from, e.g. example.com.")
    slug = models.SlugField(max_length=255, blank=True, help_text="Leave blank to generate it from the name.")
    favicon = models.ImageField(upload_to=file_upload_path, null=True, blank=True)

    meta_description = models.CharField(max_length=160, blank=True, help_text="Default search result description. Up to 160 characters.")
    og_image = models.FileField(upload_to=file_upload_path, null=True, blank=True, help_text="Default image for social media shares. Recommended size: 1200x630 px.")
    no_index = models.BooleanField(default=False, help_text="Ask search engines not to list this site.")

    header = models.FileField(upload_to=file_upload_path)
    footer = models.FileField(upload_to=file_upload_path)
    body = models.FileField(upload_to=file_upload_path, help_text="HTML file for the main page layout.")

    css_file = models.FileField(upload_to=file_upload_path)
    js_file = models.FileField(upload_to=file_upload_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sites")
    theme = models.ForeignKey(Theme, on_delete=models.PROTECT, related_name="sites", help_text="A theme cannot be deleted while sites use it.")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.name) or str(self.id)[:8]
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# page model
class Page(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, help_text="URL part of the page, unique within the site. Leave blank to generate it from the title.")
    page_type = models.CharField(max_length=255, help_text="Kind of page, e.g. home, about, contact.")
    canonical_url = models.TextField(max_length=500, default="", help_text="Preferred full URL of this page for search engines, e.g. https://example.com/about.")

    meta_title = models.CharField(max_length=70, blank=True, help_text="Title shown in search results. Up to 70 characters.")
    meta_description = models.CharField(max_length=160, blank=True, help_text="Description shown in search results. Up to 160 characters.")
    og_title = models.CharField(max_length=95, blank=True, help_text="Title shown when shared on social media. Up to 95 characters.")
    og_description = models.CharField(max_length=200, blank=True, help_text="Description shown when shared on social media. Up to 200 characters.")
    og_image = models.FileField(upload_to=file_upload_path, null=True, blank=True, help_text="Image for social media shares. Recommended size: 1200x630 px.")
    no_index = models.BooleanField(default=False, help_text="Ask search engines not to list this page.")

    html_file = models.FileField(upload_to=file_upload_path, null=True, blank=True)
    css_file = models.FileField(upload_to=file_upload_path, null=True, blank=True)
    js_file = models.FileField(upload_to=file_upload_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="pages")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["site", "slug"], name="uniq_page_slug_per_site"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            slug = slugify(self.title) or str(self.id)[:8]
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
    alt_text = models.CharField(max_length=255, blank=True, help_text="Short description for screen readers and for when the image fails to load.")

    theme = models.ForeignKey("Theme", null=True, blank=True, on_delete=models.CASCADE, related_name="image_assets", help_text="Set only for theme images. Leave empty for site or page images.")
    site = models.ForeignKey("Site", null=True, blank=True, on_delete=models.CASCADE, related_name="image_assets", help_text="Filled automatically when a page is selected.")
    page = models.ForeignKey("Page", null=True, blank=True, on_delete=models.CASCADE, related_name="image_assets", help_text="Attach the image to a specific page of the site.")

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


# video model
class Video(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=file_upload_path)
    size = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    title = models.CharField(max_length=255, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Length of the video in seconds.")
    poster = models.ImageField(upload_to=file_upload_path, null=True, blank=True, help_text="Preview image shown before the video plays.")

    theme = models.ForeignKey("Theme", null=True, blank=True, on_delete=models.CASCADE, related_name="video_assets", help_text="Set only for theme videos. Leave empty for site or page videos.")
    site = models.ForeignKey("Site", null=True, blank=True, on_delete=models.CASCADE, related_name="video_assets", help_text="Filled automatically when a page is selected.")
    page = models.ForeignKey("Page", null=True, blank=True, on_delete=models.CASCADE, related_name="video_assets", help_text="Attach the video to a specific page of the site.")

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