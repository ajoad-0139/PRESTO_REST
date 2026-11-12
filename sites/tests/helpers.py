import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage


def make_file(name, content=b"test", content_type="text/plain"):
    """
    Create a SimpleUploadedFile with the given name and content.

    Args:
        name: Name of the uploaded file.
        content: File content in bytes. Defaults to b"test".
        content_type: MIME type of the file. Defaults to "text/plain".

    Returns:
        SimpleUploadedFile: The generated uploaded file.
    """
    return SimpleUploadedFile(name, content, content_type=content_type)


def make_html(name="page.html"):
    """
    Create a test HTML file with sample HTML content.

    Args:
        name: Name of the HTML file.

    Returns:
        SimpleUploadedFile: The generated HTML file.
    """
    return make_file(name, b"<h1>Hello</h1>", "text/html")


def make_css(name="style.css"):
    """
    Create a test CSS file with sample CSS content.

    Args:
        name: Name of the CSS file.

    Returns:
        SimpleUploadedFile: The generated CSS file.
    """
    return make_file(name, b"h1 { color: red; }", "text/css")


def make_js(name="app.js"):
    """
    Create a test JavaScript file with sample JavaScript content.

    Args:
        name: Name of the JavaScript file.

    Returns:
        SimpleUploadedFile: The generated JavaScript file.
    """
    return make_file(name, b"console.log('hi');", "application/javascript")


def make_image(name="pic.png"):
    """
    Create a valid PNG image for upload tests.

    Generates a 10x10 red RGB image in memory because Django's ImageField
    uses Pillow to validate uploaded image files.

    Args:
        name: Name of the image file.

    Returns:
        SimpleUploadedFile: The generated PNG image.
    """
    buffer = io.BytesIO()
    PILImage.new("RGB", (10, 10), "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_video(name="clip.mp4"):
    """
    Create a test MP4 file with sample video bytes.

    The current video validator checks the file extension, so actual
    video content is not required for these tests.

    Args:
        name: Name of the video file.

    Returns:
        SimpleUploadedFile: The generated MP4 file.
    """
    return make_file(name, b"\x00\x00\x00 ftypmp42", "video/mp4")
