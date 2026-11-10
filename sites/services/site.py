import os
from django.core.files.base import ContentFile
from django.db import transaction
from sites.models import Site
from sites.exceptions import ThemeIncomplete

class SiteService:

    @classmethod
    def list(cls, *, user, status=None, language=None, search=None):
        sites = Site.objects.filter(created_by=user)

        if status:
            sites = sites.filter(status=status)
        if language:
            sites = sites.filter(language=language)
        if search:
            sites = sites.filter(name__icontains=search)

        return sites.order_by("-created_at")

    @classmethod
    @transaction.atomic
    def create(cls, *, created_by, theme, name: str, language: str = "en", description: str = "",
               published_domain=None, favicon=None, meta_description: str = "",
               og_image=None, no_index: bool = False) -> Site:
        
        REQUIRED_THEME_FILES = ("header", "footer", "body", "css_file")
        
        missing = [f for f in REQUIRED_THEME_FILES if not getattr(theme, f)]
        if missing:
            raise ThemeIncomplete(
                f"The selected theme is missing required files: {', '.join(missing)}."
            )
        
        site = Site(
            created_by=created_by, theme=theme, name=name, language=language, 
            description=description, published_domain=published_domain,favicon=favicon,
            meta_description=meta_description, og_image=og_image,no_index=no_index,
            header=cls._copy_file(theme.header),footer=cls._copy_file(theme.footer),
            body=cls._copy_file(theme.body),css_file=cls._copy_file(theme.css_file),
            js_file=cls._copy_file(theme.js_file),
        )
        site.save()
        return site

    @staticmethod
    def _copy_file(field_file):
        """Copy a theme file so the site owns its own copy (None if the theme has none)."""

        if not field_file:
            return None
        field_file.open("rb")
        try:
            content = field_file.read()
        finally:
            field_file.close()
        return ContentFile(content, name=os.path.basename(field_file.name))