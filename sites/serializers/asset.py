from rest_framework import serializers
from sites.models import Image, Video

class ImageOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ["id", "file", "width", "height", "size", "alt_text", "created_at"]
        read_only_fields = fields


class VideoOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ["id", "file", "title", "duration", "size", "poster", "created_at"]
        read_only_fields = fields