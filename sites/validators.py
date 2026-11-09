from rest_framework import serializers
from django.core.validators import FileExtensionValidator

IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp", "svg")
VIDEO_EXTENSIONS = ("mp4", "webm", "mov", "m4v", "ogv")
HTML_EXTENSIONS = ("html", "htm")
CSS_EXTENSIONS = ("css",)
JS_EXTENSIONS = ("js",)

video_validator = FileExtensionValidator(allowed_extensions=list(VIDEO_EXTENSIONS))
image_validator = FileExtensionValidator(allowed_extensions=list(IMAGE_EXTENSIONS) + ["ico"])
html_validator = FileExtensionValidator(allowed_extensions=list(HTML_EXTENSIONS))
css_validator = FileExtensionValidator(allowed_extensions=list(CSS_EXTENSIONS))
js_validator = FileExtensionValidator(allowed_extensions=list(JS_EXTENSIONS))

def validate_max_size(max_bytes):
    """Validator factory: reusable size check for any uploaded file."""
    def validator(file):
        if file.size > max_bytes:
            raise serializers.ValidationError(
                f"File too large. Max allowed size is {max_bytes // 1024} KB."
            )
    return validator
