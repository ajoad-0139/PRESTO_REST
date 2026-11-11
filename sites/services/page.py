from sites.services.site import SiteService
from sites.models import Page
from sites.utils import StorageCleaner
from sites.exceptions import PageAlreadyExists, PageNotFound
from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError, PermissionDenied

class PageService :
    @classmethod
    def list(cls, *, site_id, page_type=None, search=None):
        site = SiteService.get(site_id=site_id)
        pages = site.pages.order_by("-created_at")

        if page_type:
            pages = pages.filter(page_type__iexact=page_type)
        if search:
            pages = pages.filter(title__icontains=search)

        return pages

    @classmethod
    def create(cls, *, site_id, user, title: str, page_type: str, **data) -> Page:
        site = SiteService.get(site_id=site_id)

        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't add pages to this site.")

        if site.pages.filter(title__iexact=title).exists():
            raise PageAlreadyExists()

        slug = slugify(title)
        cls._ensure_unique(site, title, slug)
        page = Page(site=site, title=title, page_type=page_type, slug=slug, **data)

        try:
            page.save()
        except Exception:
            StorageCleaner.delete_written_files(page)
            raise

        return page

    @classmethod
    def get(cls, *, site_id, page_id) -> Page:
        _, page = cls._get_page(site_id=site_id, page_id=page_id)
        return page

    @classmethod
    def _get_page(cls, *, site_id, page_id):
        site = SiteService.get(site_id=site_id)
        try:
            page = site.pages.get(pk=page_id)
        except Page.DoesNotExist:
            raise PageNotFound()
        return site, page

    @staticmethod
    def _ensure_unique(site, title, slug, exclude_pk=None):
        pages = site.pages.exclude(pk=exclude_pk) if exclude_pk else site.pages.all()
        if pages.filter(title__iexact=title).exists():
            raise PageAlreadyExists()
        if slug and pages.filter(slug=slug).exists():
            raise PageAlreadyExists()

    FILE_FIELDS = ("html_file", "css_file", "js_file", "og_image")

    @classmethod
    def update(cls, *, site_id, page_id, user, **data) -> Page:
        site, page = cls._get_page(site_id=site_id, page_id=page_id)
        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't edit this page.")

        new_title = data.get("title")
        if new_title:
            slug = slugify(new_title)
            cls._ensure_unique(site, new_title, slug, exclude_pk=page.pk)
            if new_title != page.title:
                page.slug = slug or str(page.id)[:8]

        old_files = {}
        for field in cls.FILE_FIELDS:
            if field in data:
                current = getattr(page, field)
                if current:
                    old_files[field] = (current.storage, current.name)

        for field, value in data.items():
            setattr(page, field, value)

        try:
            page.save()
        except Exception:
            for field in cls.FILE_FIELDS:
                if field not in data:
                    continue
                new = getattr(page, field)
                old_name = old_files.get(field, (None, None))[1]
                if new and getattr(new, "_committed", False) and new.name != old_name:
                    StorageCleaner.delete_files(new.storage, new.name)
            raise

        for field, (old_storage, old_name) in old_files.items():
            new = getattr(page, field)
            if not new or new.name != old_name:
                transaction.on_commit(lambda s=old_storage, n=old_name: StorageCleaner.delete_files(s, n))

        return page

    @classmethod
    @transaction.atomic
    def delete(cls, *, site_id, page_id, user) -> None:
        site, page = cls._get_page(site_id=site_id, page_id=page_id)
        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't delete this page.")

        files = cls._collect_files(page)   

        page.delete()   

        for storage, name in files:
            transaction.on_commit(lambda s=storage, n=name: StorageCleaner.delete_files(s, n))

    @staticmethod
    def _collect_files(page):
        fields = [page.html_file, page.css_file, page.js_file, page.og_image]
        for image in page.image_assets.all():
            fields.append(image.file)
        for video in page.video_assets.all():
            fields.extend([video.file, video.poster])
        return [(f.storage, f.name) for f in fields if f and f.name]
