import os
import logging
from django.db import transaction
from django.db.models import ProtectedError
from sites.models import Theme, Image, Video
from rest_framework.exceptions import PermissionDenied
from sites.utils import StorageCleaner
from django.utils.text import slugify
from sites.exceptions import (ThemeAlreadyExists, ThemeNotFound, ThemeInUse,
    ImageNotFound, VideoNotFound)

logger = logging.getLogger(__name__)

class ThemeService :
    @classmethod
    @transaction.atomic
    def create(cls, *, name: str, thumbnail, header,footer, body, 
               css_file, language: str = "en", js_file=None, slug: str = "",
               description: str = "", is_active: bool = True, created_by) -> Theme:
        
        themes = Theme.objects.filter(name__iexact=name, language=language)
        if themes.exists():
            raise ThemeAlreadyExists()

        theme = Theme(
            name=name, slug=slug, description=description, is_active=is_active,
            language=language, thumbnail=thumbnail, header=header, footer=footer,
            body=body, css_file=css_file, js_file=js_file, created_by=created_by
        )
        
        theme.save()

        return theme

    @classmethod
    def list(cls, *, is_active=None, language=None, search=None):
        themes = Theme.objects.order_by("-created_at")

        if is_active is not None:
            themes = themes.filter(is_active=is_active)
        if language:
            themes = themes.filter(language=language)
        if search:
            themes = themes.filter(name__icontains=search)

        return themes

    @classmethod
    def get(cls, *, theme_id) -> Theme:
        try:
            return Theme.objects.get(pk=theme_id)
        except Theme.DoesNotExist:
            raise ThemeNotFound()

    FILE_FIELDS = ("thumbnail", "header", "footer", "body", "css_file", "js_file")

    @classmethod
    def update(cls, *, theme_id, user, **data) -> Theme:
        theme = cls.get(theme_id=theme_id)
        if not (user.is_staff or theme.created_by_id == user.id):
            raise PermissionDenied("You can't edit this theme.")

        if "name" in data or "language" in data:
            name = data.get("name", theme.name)
            language = data.get("language", theme.language)
            duplicates = Theme.objects.filter(name__iexact=name, language=language).exclude(pk=theme.pk)
            if duplicates.exists():
                raise ThemeAlreadyExists()

        if "name" in data and "slug" not in data and data["name"] != theme.name:
            theme.slug = slugify(data["name"]) or str(theme.id)[:8]

        old_files = {}
        for field in cls.FILE_FIELDS:
            if field in data:
                current = getattr(theme, field)
                if current:
                    old_files[field] = (current.storage, current.name)

        for field, value in data.items():
            setattr(theme, field, value)

        try:
            theme.save()
        except Exception:
            for field in cls.FILE_FIELDS:
                if field not in data:
                    continue
                new = getattr(theme, field)
                old_name = old_files.get(field, (None, None))[1]
                if new and getattr(new, "_committed", False) and new.name != old_name:
                    StorageCleaner.delete_files(new.storage, new.name)
            raise

        for field, (old_storage, old_name) in old_files.items():
            new = getattr(theme, field)
            if not new or new.name != old_name:
                transaction.on_commit(lambda s=old_storage, n=old_name: StorageCleaner.delete_files(s, n))

        return theme

    @classmethod
    @transaction.atomic
    def delete(cls, *, theme_id, user) -> None:
        theme = cls.get(theme_id=theme_id)

        if not (user.is_staff or theme.created_by_id == user.id):
            raise PermissionDenied("You can't delete this theme.")

        if theme.sites.exists():
            raise ThemeInUse()

        files = cls._collect_files(theme)
        
        try:
            theme.delete()
        except ProtectedError:
            raise ThemeInUse()

        transaction.on_commit(lambda: cls._delete_files(files))

    @staticmethod
    def _collect_files(theme):
        fields = [theme.thumbnail, theme.header, theme.footer, theme.body, theme.css_file, theme.js_file]
        for image in theme.image_assets.all():
            fields.append(image.file)
        for video in theme.video_assets.all():
            fields.extend([video.file, video.poster])
        return [(f.storage, f.name) for f in fields if f and f.name]


    @staticmethod
    def _delete_files(files):
        for storage, name in files:
            try:
                storage.delete(name)
            except Exception:
                logger.exception("Could not delete file %s", name)

                

class ThemeImageService :
    @staticmethod
    def _get_theme(theme_id) -> Theme:
        try:
            return Theme.objects.get(pk=theme_id)
        except Theme.DoesNotExist:
            raise ThemeNotFound()
        
    @classmethod
    def list(cls, *, theme_id):
        theme = cls._get_theme(theme_id)
        return theme.image_assets.order_by("-created_at")
        
    @classmethod
    @transaction.atomic
    def create(cls, *, theme_id, user, files, alt_text: str = "") -> "list[Image]":
        theme = cls._get_theme(theme_id)

        if not (user.is_staff or theme.created_by_id == user.id):
            raise PermissionDenied("You can't add images to this theme.")

        images = []
        try:
            for file in files:
                images.append(Image.objects.create(theme=theme, file=file, alt_text=alt_text))
        except Exception:
            for image in images:
                image.file.storage.delete(image.file.name)
            raise

        return images

    @classmethod
    def get(cls, *, theme_id, image_id) -> Image:
        _, image = cls._get_image(theme_id=theme_id, image_id=image_id)
        return image

    @classmethod
    def _get_image(cls, *, theme_id, image_id):
        theme = ThemeService.get(theme_id=theme_id)

        try:
            image = Image.objects.get(pk=image_id, theme=theme)
        except Image.DoesNotExist:
            raise ImageNotFound()

        return theme, image

    @classmethod
    def update(cls, *, theme_id, image_id, user, **data) -> Image:
        theme, image = cls._get_image(theme_id=theme_id, image_id=image_id)

        if not (user.is_staff or theme.created_by_id == user.id):
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
            if (replacing and new and getattr(new, "_committed", False) and new.name != old_name):
                StorageCleaner.delete_files(new.storage, new.name)
            raise

        if old_name and image.file.name != old_name:
            transaction.on_commit(lambda: StorageCleaner.delete_files(old_storage, old_name))

        return image
    
    @classmethod
    @transaction.atomic
    def delete(cls, *, theme_id, image_id, user) -> None:
        theme, image = cls._get_image(theme_id=theme_id, image_id=image_id)

        if not (user.is_staff or theme.created_by_id == user.id):
            raise PermissionDenied("You can't delete this image.")

        storage, name = ((image.file.storage, image.file.name)if image.file else (None, None))

        image.delete()

        if name:
            transaction.on_commit(lambda: StorageCleaner.delete_files(storage, name))


class ThemeVideoService:

    @staticmethod
    def _get_theme(theme_id) -> Theme:
        try:
            return Theme.objects.get(pk=theme_id)
        except Theme.DoesNotExist:
            raise ThemeNotFound()

    @classmethod
    def list(cls, *, theme_id):
        theme = cls._get_theme(theme_id)
        return theme.video_assets.order_by("-created_at")

    @classmethod
    @transaction.atomic
    def create(cls, *, theme_id, user, files) -> "list[Video]":
        theme = cls._get_theme(theme_id)

        if not (user.is_staff or theme.created_by_id == user.id):
            raise PermissionDenied("You can't add videos to this theme.")

        videos = []
        try:
            for file in files:
                title = os.path.splitext(file.name)[0][:255]
                videos.append(Video.objects.create(theme=theme, file=file, title=title))
        except Exception:
            # rows roll back, but files already written would be orphaned
            for video in videos:
                video.file.storage.delete(video.file.name)
            raise

        return videos


    @classmethod
    def get(cls, *, theme_id, video_id) -> Video:
        _, video = cls._get_video(theme_id=theme_id, video_id=video_id)
        return video

    @classmethod
    def _get_video(cls, *, theme_id, video_id):
        theme = ThemeService.get(theme_id=theme_id)

        try:
            video = Video.objects.get(pk=video_id, theme=theme)
        except Video.DoesNotExist:
            raise VideoNotFound()

        return theme, video

    FILE_FIELDS = ("file", "poster")
    
    @classmethod
    def update(cls, *, theme_id, video_id, user, **data) -> Video:
        theme, video = cls._get_video(theme_id=theme_id, video_id=video_id)

        if not (user.is_staff or theme.created_by_id == user.id):
            raise PermissionDenied("You can't edit this video.")

        old_files = {}
        for field in cls.FILE_FIELDS:
            if field in data:
                current = getattr(video, field)
                if current:
                    old_files[field] = (current.storage, current.name)

        for field, value in data.items():
            setattr(video, field, value)

        if "file" in data:
            video.duration = None

        try:
            video.save()
        except Exception:
            for field in cls.FILE_FIELDS:
                if field not in data:
                    continue

                new = getattr(video, field)
                old_name = old_files.get(field, (None, None))[1]

                if (new and getattr(new, "_committed", False) and new.name != old_name):
                    StorageCleaner.delete_files(new.storage, new.name)
            raise

        for field, (old_storage, old_name) in old_files.items():
            new = getattr(video, field)

            if not new or new.name != old_name:
                transaction.on_commit(lambda s=old_storage, n=old_name: StorageCleaner.delete_files(s, n))

        return video


    @classmethod
    @transaction.atomic
    def delete(cls, *, theme_id, video_id, user) -> None:
        theme, video = cls._get_video(theme_id=theme_id, video_id=video_id)

        if not (user.is_staff or theme.created_by_id == user.id):
            raise PermissionDenied("You can't delete this video.")

        files = [(getattr(video, field).storage, getattr(video, field).name) for field in cls.FILE_FIELDS if getattr(video, field)]

        video.delete()

        for storage, name in files:
            transaction.on_commit(lambda s=storage, n=name: StorageCleaner.delete_files(s, n))
