import os

def file_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower().lstrip(".")
 
    if extension == "css":
        folder = "css"
    elif extension == "js":
        folder = "js"
    elif extension in ["jpg", "jpeg", "png", "gif", "webp", "svg"]:
        folder = "images"
    elif extension in ["pdf", "doc", "docx"]:
        folder = "documents"
    else:
        folder = "others"
 
    # theme files may be uploaded before the theme row exists
    if instance.site_id:
        owner = f"sites/{instance.site_id}"
    else:
        owner = f"themes/{instance.theme_id or 'unassigned'}"
 
    return f"{owner}/{folder}/{filename}"