# sites/tests/helpers.py
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage


def make_file(name, content=b"test", content_type="text/plain"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def make_html(name="page.html"):
    return make_file(name, b"<h1>Hello</h1>", "text/html")


def make_css(name="style.css"):
    return make_file(name, b"h1 { color: red; }", "text/css")


def make_js(name="app.js"):
    return make_file(name, b"console.log('hi');", "application/javascript")


def make_image(name="pic.png"):
    # ImageField runs Pillow on the upload, so this must be a real image
    buffer = io.BytesIO()
    PILImage.new("RGB", (10, 10), "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_video(name="clip.mp4"):
    # the validator only checks the extension, so fake bytes are enough
    return make_file(name, b"\x00\x00\x00 ftypmp42", "video/mp4")