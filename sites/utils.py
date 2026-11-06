import os

FOLDERS = {
    "css": "css",
    "js": "js",
    "html": "html",
    **dict.fromkeys(["jpg", "jpeg", "png", "gif", "webp", "svg", "ico"], "images"),
    **dict.fromkeys(["mp4", "webm", "mov", "m4v", "ogv"], "videos"),
    **dict.fromkeys(["pdf", "doc", "docx"], "documents"),
}


def file_upload_path(instance, filename):
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