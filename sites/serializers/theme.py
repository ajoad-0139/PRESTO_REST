from sites.models import Theme
from rest_framework import serializers
from sites.serializers.asset import ImageOutputSerializer, VideoOutputSerializer
from sites.validators import validate_max_size, image_validator, html_validator, css_validator, js_validator, video_validator
from sites.utils.constraints import MAX_CSS_SIZE, MAX_HTML_SIZE, MAX_JS_SIZE, MAX_THUMBNAIL_SIZE, SUPPORTED_LANGUAGES, MAX_IMAGE_SIZE, MAX_VIDEO_SIZE


class ThemeCreateInputSerializer(serializers.ModelSerializer):
    """
    Validate and deserialize input data for creating a theme.

    Handles theme details, language, activation status, thumbnail,
    HTML content files, CSS, JavaScript, and the authenticated creator.
    """

    class Meta:
        """
        Configure the Theme model and accepted input fields.
        """

        model = Theme
        fields = [
            "id", "name", "slug", "description", "is_active", "language",
            "thumbnail", "header", "footer", "body", "css_file", "js_file",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    is_active = serializers.BooleanField(default=True)
    
    header = serializers.FileField(validators=[html_validator,validate_max_size(MAX_HTML_SIZE)])
    footer = serializers.FileField(validators=[html_validator,validate_max_size(MAX_HTML_SIZE)])
    body = serializers.FileField(validators=[html_validator,validate_max_size(MAX_HTML_SIZE)])
    css_file = serializers.FileField(validators=[css_validator, validate_max_size(MAX_CSS_SIZE)])
    js_file = serializers.FileField(required=False, allow_null=True, validators=[js_validator, validate_max_size(MAX_JS_SIZE)])
    thumbnail = serializers.ImageField(validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def validate_name(self, value):
        """
        Strip whitespace from the theme name and ensure it has at least
        three characters.

        Args:
            value: Theme name provided in the request.

        Returns:
            str: Cleaned theme name.

        Raises:
            serializers.ValidationError: If the name has fewer than
                three characters.
        """

        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters.")
        return value

    def validate_language(self, value):
        """
        Normalize the language code and check whether it is supported.

        Args:
            value: Language code provided in the request.

        Returns:
            str: Normalized language code.

        Raises:
            serializers.ValidationError: If the language is unsupported.
        """

        value = value.strip().lower()
        if value not in SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(
                f"Unsupported language. Choose from: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
            )
        return value


class ThemeOuputSerializer(serializers.ModelSerializer):
    """
    Serialize theme data for API responses.

    Returns theme details, activation status, language, thumbnail,
    HTML/CSS/JavaScript files, creator, and timestamps.
    """

    class Meta:
        """
        Configure the Theme model and read-only output fields.
        """

        model = Theme
        fields = [
            "id", "name", "slug", "description", "is_active", "language",
            "thumbnail", "header", "footer", "body", "css_file", "js_file",
            "created_by", "created_at", "updated_at", 
        ]
        read_only_fields = fields


class ThemeListQuerySerializer(serializers.Serializer):
    """
    Validate query parameters for filtering and searching themes.

    Supports filtering by activation status and language, and searching
    by a text query.
    """

    is_active = serializers.BooleanField(required=False)
    language = serializers.CharField(required=False)
    search = serializers.CharField(required=False)


class ThemeImageCreateInputSerializer(serializers.Serializer):
    """
    Validate input data for uploading multiple images to a theme.

    Accepts a non-empty list of up to ten validated image files
    and optional alternative text.
    """

    files = serializers.ListField(
        child=serializers.ImageField(validators=[image_validator, validate_max_size(MAX_IMAGE_SIZE)]),
        allow_empty=False,
        max_length=10,         
    )
    alt_text = serializers.CharField(max_length=255, required=False, allow_blank=True)

class ThemeImageOutputSerializer(ImageOutputSerializer):
    """
    Serialize theme image data for API responses.

    Extends the base image output serializer without adding fields.
    """

    class Meta(ImageOutputSerializer.Meta):
        """
        Reuse the base image output fields as read-only fields.
        """

        fields = ImageOutputSerializer.Meta.fields
        read_only_fields = fields


class ThemeImageUpdateInputSerializer(serializers.Serializer):
    """
    Validate input data for updating a theme image.

    Supports replacing the image file and updating its alternative text.
    """

    file = serializers.ImageField(required=False,validators=[image_validator,validate_max_size(MAX_IMAGE_SIZE)])
    alt_text = serializers.CharField(max_length=255,required=False,allow_blank=True)


class ThemeVideoCreateInputSerializer(serializers.Serializer):
    """
    Validate input data for uploading multiple videos to a theme.

    Accepts a non-empty list of up to five validated video files.
    """

    files = serializers.ListField(
        child=serializers.FileField(validators=[video_validator, validate_max_size(MAX_VIDEO_SIZE)]),
        allow_empty=False,
        max_length=5,         
    )


class ThemeVideoOutputSerializer(VideoOutputSerializer):
    """
    Serialize theme video data for API responses.

    Extends the base video output serializer without adding fields.
    """

    class Meta(VideoOutputSerializer.Meta):
        fields = VideoOutputSerializer.Meta.fields
        read_only_fields = fields



class ThemeVideoUpdateInputSerializer(serializers.Serializer):
    """
    Validate input data for updating a theme video.

    Supports replacing the video file and updating its title
    or poster image.
    """
    
    file = serializers.FileField(required=False,validators=[video_validator, validate_max_size(MAX_VIDEO_SIZE)])
    title = serializers.CharField(max_length=255,required=False, allow_blank=True)
    poster = serializers.ImageField(required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])
