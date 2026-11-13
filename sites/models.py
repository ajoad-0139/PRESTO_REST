"""Define database models for themes, sites, pages, images, and videos."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from sites.utils.storage import file_upload_path


class Theme(models.Model):
    """Store reusable website themes and their layout assets."""

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
        """Generate a slug from the theme name when one is not provided."""
        if not self.slug:
            slug = slugify(self.name) or str(self.id)[:8]
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the theme name."""
        return self.name


class Site(models.Model):
    """Store website details, publishing settings, and theme configuration."""

    class Status(models.TextChoices):
        """Define the available publishing states for a site."""

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
        """Define the default ordering and database indexes for sites."""

        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        """Generate a slug from the site name when one is not provided."""
        if not self.slug:
            slug = slugify(self.name) or str(self.id)[:8]
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the site name."""
        return self.name


class Page(models.Model):
    """Store individual pages and their content and SEO metadata."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, help_text="URL part of the page, Leave blank to generate it from the title.")
    page_type = models.CharField(max_length=255, help_text="Kind of page, e.g. home, about, contact.")
    canonical_url = models.TextField(max_length=500, default="", help_text="Preferred full URL of this page for search engines, e.g. [https://example.com/about](https://example.com/about).")

    meta_title = models.CharField(max_length=70, blank=True, help_text="Title shown in search results. Up to 70 characters.")
    meta_description = models.CharField(max_length=160, blank=True, help_text="Description shown in search results. Up to 160 characters.")
    og_title = models.CharField(max_length=95, blank=True, help_text="Title shown when shared on social media. Up to 95 characters.")
    og_description = models.CharField(max_length=200, blank=True, help_text="Description shown when shared on social media. Up to 200 characters.")
    no_index = models.BooleanField(default=False, help_text="Ask search engines not to list this page.")

    og_image = models.FileField(upload_to=file_upload_path, null=True, blank=True, max_length=255, help_text="Image for social media shares. Recommended size: 1200x630 px.")
    html_file = models.FileField(upload_to=file_upload_path, max_length=255,)
    css_file = models.FileField(upload_to=file_upload_path, max_length=255,)
    js_file = models.FileField(upload_to=file_upload_path, max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="pages")

    class Meta:
        """Ensure page slugs are unique within each site."""

        constraints = [
            models.UniqueConstraint(fields=["site", "slug"], name="uniq_page_slug_per_site"),
        ]

    def save(self, *args, **kwargs):
        """Generate a slug from the page title when one is not provided."""
        if not self.slug:
            slug = slugify(self.title) or str(self.id)[:8]
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the page title."""
        return self.title


class Image(models.Model):
    """Store image assets associated with themes, sites, or pages."""

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
        """Enforce valid ownership combinations for image assets."""

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
        """Assign the page's site and validate that both belong together."""
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id
        if self.page_id and self.page.site_id != self.site_id:
            raise ValidationError({"page": "Page belongs to a different site."})

    def save(self, *args, **kwargs):
        """Validate image ownership and update the stored file size."""
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id
        self.clean()
        if self.file:
            self.size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the image file name."""
        return self.file.name


class Video(models.Model):
    """Store video assets associated with themes, sites, or pages."""

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
        """Enforce valid ownership combinations for video assets."""

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
        """Assign the page's site and validate that both belong together."""
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id
        if self.page_id and self.page.site_id != self.site_id:
            raise ValidationError({"page": "Page belongs to a different site."})

    def save(self, *args, **kwargs):
        """Validate video ownership and update the stored file size."""
        if self.page_id and not self.site_id:
            self.site_id = self.page.site_id
        self.clean()
        if self.file:
            self.size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        """Return the video title or file name."""
        return self.title or self.file.name