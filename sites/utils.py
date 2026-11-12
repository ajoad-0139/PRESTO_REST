"""Provide file upload path generation and storage cleanup utilities."""

import logging
import os

from django.db.models import FileField

logger = logging.getLogger(__name__)

FOLDERS = {
    "css": "css",
    "js": "js",
    "html": "html",
    **dict.fromkeys(["jpg", "jpeg", "png", "gif", "webp", "svg", "ico"], "images"),
    **dict.fromkeys(["mp4", "webm", "mov", "m4v", "ogv"], "videos"),
    **dict.fromkeys(["pdf", "doc", "docx"], "documents"),
}


def file_upload_path(instance, filename):
    """Generate an organized upload path based on file type and model owner."""
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    folder = FOLDERS.get(ext, "others")
    model = instance._meta.model_name

    if model in ("image", "video"):
        owner = f"sites/{instance.site_id}" if instance.site_id else f"themes/{instance.theme_id}"
    elif model == "theme":
        owner = f"themes/{instance.pk}"
    elif model == "site":
        owner = f"sites/{instance.pk}"
    elif model == "page":
        owner = f"sites/{instance.site_id}/pages/{instance.pk}"
    else:
        raise ValueError(f"file_upload_path: unsupported model '{model}'")

    return f"{owner}/{folder}/{filename}"


class StorageCleaner:
    """Provide utilities for deleting files from storage."""

    @staticmethod
    def delete_written_files(instance):
        """Delete files already written to storage for a new model instance."""
        for field in instance._meta.concrete_fields:
            if not isinstance(field, FileField):
                continue

            file = getattr(instance, field.name)
            if file and getattr(file, "_committed", False):
                try:
                    file.storage.delete(file.name)
                except Exception:
                    logger.exception("Could not delete file %s", file.name)

    @staticmethod
    def delete_files(storage, name):
        """Delete a named file from the specified storage backend."""
        try:
            storage.delete(name)
        except Exception:
            logger.exception("Could not delete file %s", name)