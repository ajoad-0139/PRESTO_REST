import os
import logging
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify
from sites.utils import StorageCleaner
from sites.models import Site, Image, Video
from rest_framework.exceptions import ValidationError, PermissionDenied
from sites.exceptions import ThemeIncomplete, SiteNotFound, ImageNotFound, VideoNotFound

logger = logging.getLogger(__name__)

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

    @classmethod
    def get(cls, *, site_id) -> Site:
        sites = Site.objects.all() 
        try:
            return sites.get(pk=site_id)
        except Site.DoesNotExist:
            raise SiteNotFound()




    FILE_FIELDS = ("favicon", "og_image")

    @classmethod
    def update(cls, *, site, **data):
        status = data.get("status", site.status)
        domain = data.get("published_domain", site.published_domain)

        if status == Site.Status.PUBLISHED and not domain:
            raise ValidationError({
                "published_domain": ["A domain is required to publish a site."]
            })

        new_name = data.get("name")
        if new_name and new_name != site.name:
            new_slug = slugify(new_name)
            site.slug = new_slug

        old_files = []
        old_names = {}
        for field in cls.FILE_FIELDS:
            if field in data:
                old_file = getattr(site, field)
                if old_file:
                    old_files.append((old_file.storage, old_file.name))
                    old_names[field] = old_file.name

        for field, value in data.items():
            setattr(site, field, value)

        try:
            site.save()
        except Exception:
            cls._delete_new_files(site, data, old_names)
            raise

        current = {getattr(site, f).name for f in cls.FILE_FIELDS if getattr(site, f)}
        to_delete = [(s, n) for s, n in old_files if n not in current]
        transaction.on_commit(lambda: cls._delete_files(to_delete))

        return site

    @classmethod
    def _delete_new_files(cls, site, data, old_names):
        for field in cls.FILE_FIELDS:
            if field not in data:
                continue

            new_file = getattr(site, field)
            if new_file and new_file._committed and new_file.name != old_names.get(field):
                try:
                    new_file.storage.delete(new_file.name)
                except Exception:
                    logger.exception("Could not delete file %s", new_file.name)

    @staticmethod
    def _delete_files(files):
        for storage, name in files:
            try:
                storage.delete(name)
            except Exception:
                logger.exception( "Could not delete file %s",name)

    @classmethod
    @transaction.atomic
    def delete(cls, *, site_id, user) -> None:
        site = cls.get(site_id=site_id)

        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't delete this site.")

        files = cls._collect_files(site)   
        site.delete()                      

        transaction.on_commit(lambda: cls._delete_files(files))


    @staticmethod
    def _collect_files(site):
        fields = [
            site.favicon, site.og_image,
            site.header, site.footer, site.body, site.css_file, site.js_file,
        ]
        for page in site.pages.all():
            fields.extend([page.html_file, page.css_file, page.js_file, page.og_image])
        for image in site.image_assets.all():     
            fields.append(image.file)
        for video in site.video_assets.all():   
            fields.extend([video.file, video.poster])
        return [(f.storage, f.name) for f in fields if f and f.name]



class SiteImageService:

    @classmethod
    def list(cls, *, site_id, page=None):
        site = SiteService.get(site_id=site_id)
        images = site.image_assets.order_by("-created_at")
        if page:
            images = images.filter(page_id=page)
        return images


    @classmethod
    @transaction.atomic
    def create(cls, *, site_id, user, files, alt_text: str = "", page=None) -> "list[Image]":
        site = SiteService.get(site_id=site_id)

        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't add images to this site.")

        if page is not None and page.site_id != site.id:
            raise ValidationError({"page": ["This page belongs to a different site."]})

        images = []
        try:
            for file in files:
                image = Image(site=site, page=page, file=file, alt_text=alt_text)
                try:
                    image.save()
                except Exception:
                    StorageCleaner.delete_written_files(image)
                    raise
                images.append(image)
        except Exception:
            for image in images:
                image.file.storage.delete(image.file.name)
            raise

        return images

    @classmethod
    def get(cls, *, site_id, image_id) -> Image:
        _, image = cls._get_image(site_id=site_id, image_id=image_id)
        return image

    @classmethod
    def _get_image(cls, *, site_id, image_id):
        site = SiteService.get(site_id=site_id)
        try:
            image = Image.objects.get(pk=image_id, site=site)
        except Image.DoesNotExist:
            raise ImageNotFound()
        return site, image

    @classmethod
    def update(cls, *, site_id, image_id, user, **data) -> Image:
        site, image = cls._get_image(site_id=site_id, image_id=image_id)
        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't edit this image.")

        replacing = "file" in data
        old_storage = old_name = None
        if replacing and image.file:
            old_storage, old_name = image.file.storage, image.file.name

        for field, value in data.items():
            setattr(image, field, value)

        try:
            image.save()   
        except Exception:
            new = image.file
            if replacing and new and getattr(new, "_committed", False) and new.name != old_name:
                StorageCleaner.delete_files(new.storage, new.name)
            raise

        if old_name and image.file.name != old_name:
            transaction.on_commit(lambda: StorageCleaner.delete_files(old_storage, old_name))

        return image

    @classmethod
    @transaction.atomic
    def delete(cls, *, site_id, image_id, user) -> None:
        site, image = cls._get_image(site_id=site_id, image_id=image_id)
        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't delete this image.")

        storage, name = (image.file.storage, image.file.name) if image.file else (None, None)

        image.delete()

        if name:
            transaction.on_commit(lambda: StorageCleaner.delete_files(storage, name))

class SiteVideoService:

    @classmethod
    def list(cls, *, site_id, page=None):
        site = SiteService.get(site_id=site_id)
        videos = site.video_assets.order_by("-created_at")
        if page:
            videos = videos.filter(page_id=page)
        return videos


    @classmethod
    @transaction.atomic
    def create(cls, *, site_id, user, files, page=None) -> "list[Video]":
        site = SiteService.get(site_id=site_id)

        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't add videos to this site.")

        if page is not None and page.site_id != site.id:
            raise ValidationError({"page": ["This page belongs to a different site."]})

        videos = []
        try:
            for file in files:
                title = os.path.splitext(file.name)[0][:255]
                video = Video(site=site, page=page, file=file, title=title)
                try:
                    video.save()
                except Exception:
                    StorageCleaner.delete_written_files(video)
                    raise
                videos.append(video)
        except Exception:
            for video in videos:
                video.file.storage.delete(video.file.name)
            raise

        return videos


    @classmethod
    def get(cls, *, site_id, video_id) -> Video:
        _, video = cls._get_video(site_id=site_id, video_id=video_id)
        return video

    @classmethod
    def _get_video(cls, *, site_id, video_id):
        site = SiteService.get(site_id=site_id)
        try:
            video = Video.objects.get(pk=video_id, site=site)
        except Video.DoesNotExist:
            raise VideoNotFound()
        return site, video

    FILE_FIELDS = ("file", "poster")
    @classmethod
    def update(cls, *, site_id, video_id, user, **data) -> Video:
        site, video = cls._get_video(site_id=site_id, video_id=video_id)
        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't edit this video.")

        old_files = {}
        for field in cls.FILE_FIELDS:
            if field in data:
                current = getattr(video, field)
                if current:
                    old_files[field] = (current.storage, current.name)

        for field, value in data.items():
            setattr(video, field, value)

        try:
            video.save()
        except Exception:
            for field in cls.FILE_FIELDS:
                if field not in data:
                    continue
                new = getattr(video, field)
                old_name = old_files.get(field, (None, None))[1]
                if new and getattr(new, "_committed", False) and new.name != old_name:
                    StorageCleaner.delete_files(new.storage, new.name)
            raise

        for field, (old_storage, old_name) in old_files.items():
            new = getattr(video, field)
            if not new or new.name != old_name:
                transaction.on_commit(lambda s=old_storage, n=old_name: StorageCleaner.delete_files(s, n))

        return video

    @classmethod
    @transaction.atomic
    def delete(cls, *, site_id, video_id, user) -> None:
        site, video = cls._get_video(site_id=site_id, video_id=video_id)
        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't delete this video.")

        files = [(getattr(video, f).storage, getattr(video, f).name) for f in cls.FILE_FIELDS if getattr(video, f)]

        video.delete()

        for storage, name in files:
            transaction.on_commit(lambda s=storage, n=name: StorageCleaner.delete_files(s, n))