from rest_framework import serializers
from sites.models import Image, Video

class ImageOutputSerializer(serializers.ModelSerializer):
    """
    Serialize image data for API responses.

    Returns image metadata including file URL, dimensions, file size,
    alternative text, and creation timestamp.
    """

    class Meta:
        """
        Configure the Image model and output fields.
        """

        model = Image
        fields = ["id", "file", "width", "height", "size", "alt_text", "created_at"]
        read_only_fields = fields


class VideoOutputSerializer(serializers.ModelSerializer):
    """
    Serialize video data for API responses.

    Returns video metadata including file URL, title, duration,
    file size, poster image, and creation timestamp.
    """
    
    class Meta:
        """
        Configure the Video model and output fields.
        """

        model = Video
        fields = ["id", "file", "title", "duration", "size", "poster", "created_at"]
        read_only_fields = fields