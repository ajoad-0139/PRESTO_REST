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

    return f"sites/{instance.site_id}/{folder}/{filename}"