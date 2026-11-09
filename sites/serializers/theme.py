from sites.models import Theme
from rest_framework import serializers
from sites.models import Theme, Image, Video
from sites.validators import validate_max_size, image_validator, html_validator, css_validator, js_validator
from sites.constraints import MAX_CSS_SIZE, MAX_HTML_SIZE, MAX_JS_SIZE, MAX_THUMBNAIL_SIZE, SUPPORTED_LANGUAGES, MAX_IMAGE_SIZE


class ThemeCreateInputSerializer(serializers.ModelSerializer):

    class Meta:
        model = Theme
        fields = [
            "id", "name", "slug", "description", "is_active", "language",
            "thumbnail", "header", "footer", "body", "css_file", "js_file",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
    
    header = serializers.FileField(validators=[html_validator,validate_max_size(MAX_HTML_SIZE)])
    footer = serializers.FileField(validators=[html_validator,validate_max_size(MAX_HTML_SIZE)])
    body = serializers.FileField(validators=[html_validator,validate_max_size(MAX_HTML_SIZE)])
    css_file = serializers.FileField(validators=[css_validator, validate_max_size(MAX_CSS_SIZE)])
    js_file = serializers.FileField(required=False, allow_null=True, validators=[js_validator, validate_max_size(MAX_JS_SIZE)])
    thumbnail = serializers.ImageField(validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters.")
        return value

    def validate_language(self, value):
        value = value.strip().lower()
        if value not in SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(
                f"Unsupported language. Choose from: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
            )
        return value


class ThemeOuputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = [
            "id", "name", "slug", "description", "is_active", "language",
            "thumbnail", "header", "footer", "body", "css_file", "js_file",
            "created_by", "created_at", "updated_at", 
        ]
        read_only_fields = fields


class ThemeListQuerySerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    language = serializers.CharField(required=False)
    search = serializers.CharField(required=False)



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


class ThemeOuputSerializer(serializers.ModelSerializer):
    images = ImageOutputSerializer(source="image_assets", many=True, read_only=True)
    videos = VideoOutputSerializer(source="video_assets", many=True, read_only=True)

    class Meta:
        model = Theme
        fields = [
            "id", "name", "slug", "description", "is_active", "language",
            "thumbnail", "header", "footer", "body", "css_file", "js_file",
            "images", "videos", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = fields


class ThemeImageCreateInputSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.ImageField(validators=[image_validator, validate_max_size(MAX_IMAGE_SIZE)]),
        allow_empty=False,
        max_length=10,         
    )
    alt_text = serializers.CharField(max_length=255, required=False, allow_blank=True)
