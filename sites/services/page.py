from sites.services.site import SiteService
from sites.models import Page
from sites.utils import StorageCleaner
from sites.exceptions import PageAlreadyExists
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

        page = Page(site=site, title=title, page_type=page_type, **data)

        try:
            page.save()
        except Exception:
            StorageCleaner.delete_written_files(page)
            raise

        return page