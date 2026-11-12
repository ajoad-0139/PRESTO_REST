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
    """Provide business logic for managing sites"""

    @classmethod
    def list(cls, *, user, status=None, language=None, search=None):
        """Retrieve sites created by a user with optional filters.

        Args:
            user: User whose sites should be retrieved.
            status: Optional site status to filter by.
            language: Optional language to filter by.
            search: Optional search term to match against site names.

        Returns:
            QuerySet: Filtered sites ordered by creation date.
        """


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
        published_domain=None, favicon=None, meta_description: str = "", og_image=None, no_index: bool = False) -> Site:
        """Create a site using the selected theme's files.

        Args:
            created_by: User who owns the new site.
            theme: Theme used to initialize the site.
            name: Name of the new site.
            language: Language of the site. Defaults to "en".
            description: Optional site description.
            published_domain: Optional domain for publishing the site.
            favicon: Optional site favicon.
            meta_description: Optional SEO description.
            og_image: Optional Open Graph image.
            no_index: Whether search engines should avoid indexing the site.

        Returns:
            Site: The newly created site.

        Raises:
            ThemeIncomplete: If the theme is missing required files.
        """

        
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
        """Create an independent copy of a theme file.

        Args:
            field_file: Theme file to copy.

        Returns:
            ContentFile: A copy of the file, or None if no file is provided.
        """


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
        """Retrieve a site by its ID.

        Args:
            site_id: ID of the site to retrieve.

        Returns:
            Site: The requested site.

        Raises:
            SiteNotFound: If the site does not exist.
        """


        sites = Site.objects.all() 
        try:
            return sites.get(pk=site_id)
        except Site.DoesNotExist:
            raise SiteNotFound()




    FILE_FIELDS = ("favicon", "og_image")

    @classmethod
    def update(cls, *, site, user,  **data):
        """Update a site's information and manage its associated files.

        Args:
            site: Site instance to update.
            user: User requesting the update.
            **data: Site fields and values to update.

        Returns:
            Site: The updated site.

        Raises:
            PermissionDenied: If the user is not authorized to update the site.
            ValidationError: If the published site does not have a domain.

        Notes:
            Newly uploaded files are deleted if saving fails.
            Replaced or removed files are deleted after the transaction commits.
        """


        status = data.get("status", site.status)
        domain = data.get("published_domain", site.published_domain)

        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't edit this site.")

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
        """Delete newly uploaded files when a site update fails.

        Args:
            site: Site whose files are being updated.
            data: Fields and values supplied for the update.
            old_names: Original file names before the update.
        """


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
        """Delete files from their respective storage backends.

        Args:
            files: Iterable of storage and file-name pairs to delete.
        """


        for storage, name in files:
            try:
                storage.delete(name)
            except Exception:
                logger.exception( "Could not delete file %s",name)

    @classmethod
    @transaction.atomic
    def delete(cls, *, site_id, user) -> None:
        """Delete a site and its associated files.

        Args:
            site_id: ID of the site to delete.
            user: User requesting the deletion.

        Returns:
            None

        Raises:
            PermissionDenied: If the user is not authorized to delete the site.

        Notes:
            Associated files are deleted after the database transaction commits.
        """


        site = cls.get(site_id=site_id)

        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't delete this site.")

        files = cls._collect_files(site)   
        site.delete()                      

        transaction.on_commit(lambda: cls._delete_files(files))


    @staticmethod
    def _collect_files(site):
        """Collect storage locations of all files associated with a site.

        Args:
            site: Site whose associated files should be collected.

        Returns:
            list: Storage and file-name pairs for site files, page files,
                additional images, videos, and video posters.
        """


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
    """Provide business logic for managing site image assets."""

    @classmethod
    def list(cls, *, site_id, page=None):
        """Retrieve images belonging to a site with an optional page filter.

        Args:
            site_id: ID of the site whose images should be retrieved.
            page: Optional page ID to filter images by.

        Returns:
            QuerySet: Filtered images ordered by creation date.
        """


        site = SiteService.get(site_id=site_id)
        images = site.image_assets.order_by("-created_at")
        if page:
            images = images.filter(page_id=page)
        return images


    @classmethod
    @transaction.atomic
    def create(cls, *, site_id, user, files, alt_text: str = "", page=None) -> "list[Image]":
        """Create multiple image assets for a site.

        Args:
            site_id: ID of the site where images will be created.
            user: User requesting image creation.
            files: Image files to upload.
            alt_text: Alternative text applied to the uploaded images.
            page: Optional page to associate with the images.

        Returns:
            list[Image]: The newly created image assets.

        Raises:
            PermissionDenied: If the user is not authorized to add images.
            ValidationError: If the page belongs to another site.

        Notes:
            Uploaded files are cleaned up if saving any image fails.
        """


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
        """Retrieve an image belonging to a specific site.

        Args:
            site_id: ID of the site containing the image.
            image_id: ID of the image to retrieve.

        Returns:
            Image: The requested image.

        Raises:
            ImageNotFound: If the image does not exist.
        """


        _, image = cls._get_image(site_id=site_id, image_id=image_id)
        return image

    @classmethod
    def _get_image(cls, *, site_id, image_id):
        """Retrieve a site and one of its associated images.

        Args:
            site_id: ID of the site containing the image.
            image_id: ID of the image to retrieve.

        Returns:
            tuple: The site and its requested image.

        Raises:
            ImageNotFound: If the image does not exist.
        """


        site = SiteService.get(site_id=site_id)
        try:
            image = Image.objects.get(pk=image_id, site=site)
        except Image.DoesNotExist:
            raise ImageNotFound()
        return site, image

    @classmethod
    def update(cls, *, site_id, image_id, user, **data) -> Image:
        """Update an image and manage its associated file.

        Args:
            site_id: ID of the site containing the image.
            image_id: ID of the image to update.
            user: User requesting the update.
            **data: Image fields and values to update.

        Returns:
            Image: The updated image.

        Raises:
            PermissionDenied: If the user is not authorized to update the image.

        Notes:
            Newly uploaded files are cleaned up if saving fails.
            Replaced files are deleted after the transaction commits.
        """


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
        """Delete an image and its associated file.

        Args:
            site_id: ID of the site containing the image.
            image_id: ID of the image to delete.
            user: User requesting the deletion.

        Returns:
            None

        Raises:
            PermissionDenied: If the user is not authorized to delete the image.

        Notes:
            The associated file is deleted after the transaction commits.
        """


        site, image = cls._get_image(site_id=site_id, image_id=image_id)
        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't delete this image.")

        storage, name = (image.file.storage, image.file.name) if image.file else (None, None)

        image.delete()

        if name:
            transaction.on_commit(lambda: StorageCleaner.delete_files(storage, name))

class SiteVideoService:
    """Provide business logic for managing site video assets."""

    @classmethod
    def list(cls, *, site_id, page=None):
        """Retrieve videos belonging to a site with an optional page filter.

        Args:
            site_id: ID of the site whose videos should be retrieved.
            page: Optional page ID to filter videos by.

        Returns:
            QuerySet: Filtered videos ordered by creation date.
        """


        site = SiteService.get(site_id=site_id)
        videos = site.video_assets.order_by("-created_at")
        if page:
            videos = videos.filter(page_id=page)
        return videos


    @classmethod
    @transaction.atomic
    def create(cls, *, site_id, user, files, page=None) -> "list[Video]":
        """Create multiple video assets for a site.

        Args:
            site_id: ID of the site where videos will be created.
            user: User requesting video creation.
            files: Video files to upload.
            page: Optional page to associate with the videos.

        Returns:
            list[Video]: The newly created video assets.

        Raises:
            PermissionDenied: If the user is not authorized to add videos.
            ValidationError: If the page belongs to another site.

        Notes:
            Uploaded files are cleaned up if saving any video fails.
        """


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
        """Retrieve a video belonging to a specific site.

        Args:
            site_id: ID of the site containing the video.
            video_id: ID of the video to retrieve.

        Returns:
            Video: The requested video.

        Raises:
            VideoNotFound: If the video does not exist.
        """


        _, video = cls._get_video(site_id=site_id, video_id=video_id)
        return video

    @classmethod
    def _get_video(cls, *, site_id, video_id):
        """Retrieve a site and one of its associated videos.

        Args:
            site_id: ID of the site containing the video.
            video_id: ID of the video to retrieve.

        Returns:
            tuple: The site and its requested video.

        Raises:
            VideoNotFound: If the video does not exist.
        """


        site = SiteService.get(site_id=site_id)
        try:
            video = Video.objects.get(pk=video_id, site=site)
        except Video.DoesNotExist:
            raise VideoNotFound()
        return site, video

    FILE_FIELDS = ("file", "poster")
    @classmethod
    def update(cls, *, site_id, video_id, user, **data) -> Video:
        """Update a video and manage its associated files.

        Args:
            site_id: ID of the site containing the video.
            video_id: ID of the video to update.
            user: User requesting the update.
            **data: Video fields and values to update.

        Returns:
            Video: The updated video.

        Raises:
            PermissionDenied: If the user is not authorized to update the video.

        Notes:
            The video duration is reset when its file is replaced.
            Newly uploaded files are cleaned up if saving fails.
            Replaced or removed files are deleted after the transaction commits.
        """


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
        """Delete a video and its associated files.

        Args:
            site_id: ID of the site containing the video.
            video_id: ID of the video to delete.
            user: User requesting the deletion.

        Returns:
            None

        Raises:
            PermissionDenied: If the user is not authorized to delete the video.

        Notes:
            Associated files are deleted after the transaction commits.
        """


        site, video = cls._get_video(site_id=site_id, video_id=video_id)
        if not (user.is_staff or site.created_by_id == user.id):
            raise PermissionDenied("You can't delete this video.")

        files = [(getattr(video, f).storage, getattr(video, f).name) for f in cls.FILE_FIELDS if getattr(video, f)]

        video.delete()

        for storage, name in files:
            transaction.on_commit(lambda s=storage, n=name: StorageCleaner.delete_files(s, n))