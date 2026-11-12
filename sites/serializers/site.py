from rest_framework import serializers

from sites.models import Site, Theme, Page
from sites.validators import image_validator, validate_max_size, video_validator
from sites.serializers.asset import ImageOutputSerializer, VideoOutputSerializer
from sites.constraints import MAX_THUMBNAIL_SIZE, SUPPORTED_LANGUAGES, MAX_IMAGE_SIZE, MAX_VIDEO_SIZE


class SiteCreateInputSerializer(serializers.ModelSerializer):
    """
    Validate and deserialize input data for creating a site.

    Handles site details, language, active theme selection, domain,
    favicon, Open Graph image, and the authenticated creator.
    """

    class Meta:
        """
        Configure the Site model and accepted input fields.
        """

        model = Site
        fields = [
            "name", "description", "language", "theme", "published_domain",
            "favicon", "meta_description", "og_image", "no_index", "created_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    theme = serializers.PrimaryKeyRelatedField(queryset=Theme.objects.filter(is_active=True))
    favicon = serializers.ImageField(required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])
    og_image = serializers.FileField( required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])
    created_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def validate_name(self, value):
        """
        Strip whitespace from the site name and ensure it has at least
        three characters.

        Args:
            value: Site name provided in the request.

        Returns:
            str: Cleaned site name.

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

    def validate_published_domain(self, value):
        """
        Normalize the published domain by stripping whitespace and
        converting it to lowercase.

        Args:
            value: Published domain provided in the request.

        Returns:
            str or None: Normalized domain, or None if empty.
        """

        value = (value or "").strip().lower()
        return value or None


class SiteListQuerySerializer(serializers.Serializer):
    """
    Validate query parameters for filtering and searching sites.

    Supports filtering by site status and language, and searching
    by a text query.
    """

    status = serializers.ChoiceField(choices=Site.Status.choices, required=False)
    language = serializers.CharField(required=False)
    search = serializers.CharField(required=False)


class SiteOutputSerializer(serializers.ModelSerializer):
    """
    Serialize site data for API responses.

    Returns site details, publication status, SEO metadata, assets,
    page content, theme, creator, and timestamps.
    """

    class Meta:
        """
        Configure the Site model and read-only output fields.
        """

        model = Site
        fields = [
            "id", "name", "slug", "description", "language", "status",
            "published_domain", "favicon", "meta_description", "og_image", "no_index",
            "header", "footer", "body", "css_file", "js_file",
            "theme", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = fields


class SiteUpdateInputSerializer(serializers.ModelSerializer):
    """
    Validate input data for updating an existing site.

    Supports partial updates to site details, language, status,
    published domain, favicon, SEO metadata, and Open Graph image.
    """

    class Meta:
        """
        Configure the Site model and accepted update fields.
        """

        model = Site
        fields = [
            "name", "description", "language", "status", "published_domain",
            "favicon", "meta_description", "og_image", "no_index",
        ]

    favicon = serializers.ImageField( required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])
    og_image = serializers.FileField( required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])

    def validate_name(self, value):
        """
        Strip whitespace from the site name and ensure it has at least
        three characters.

        Args:
            value: Site name provided in the request.

        Returns:
            str: Cleaned site name.

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

    def validate_published_domain(self, value):
        """
        Normalize the published domain by stripping whitespace and
        converting it to lowercase.

        Args:
            value: Published domain provided in the request.

        Returns:
            str or None: Normalized domain, or None if empty.
        """

        value = (value or "").strip().lower()
        return value or None


class SiteImageCreateInputSerializer(serializers.Serializer):
    """
    Validate input data for uploading multiple images to a site.

    Accepts a non-empty list of up to ten validated image files,
    optional alternative text, and an optional associated page.
    """

    files = serializers.ListField(
        child=serializers.ImageField(validators=[image_validator, validate_max_size(MAX_IMAGE_SIZE)]),
        allow_empty=False, 
        max_length=10,
    )
    alt_text = serializers.CharField(max_length=255, required=False, allow_blank=True)
    page = serializers.PrimaryKeyRelatedField(queryset=Page.objects.all(), required=False, allow_null=True)


class SiteImageListQuerySerializer(serializers.Serializer):
    """
    Validate query parameters for filtering site images by page UUID.
    """

    page = serializers.UUIDField(required=False)


class SiteImageOutputSerializer(ImageOutputSerializer):
    """
    Serialize site image data for API responses.

    Extends the base image output with the associated page field.
    """

    class Meta(ImageOutputSerializer.Meta):
        """
        Extend the base image output fields with the page field.
        """

        fields = ImageOutputSerializer.Meta.fields + ["page"]
        read_only_fields = fields

class SiteImageUpdateInputSerializer(serializers.Serializer):
    """
    Validate input data for updating a site image.

    Supports replacing the image file and updating its alternative text.
    """

    file = serializers.ImageField(
        required=False,
        validators=[image_validator, validate_max_size(MAX_IMAGE_SIZE)],
    )
    alt_text = serializers.CharField(max_length=255, required=False, allow_blank=True)

class SiteVideoCreateInputSerializer(serializers.Serializer):
    """
    Validate input data for uploading multiple videos to a site.

    Accepts a non-empty list of up to five validated video files
    and an optional associated page.
    """

    files = serializers.ListField(
        child=serializers.FileField(validators=[video_validator, validate_max_size(MAX_VIDEO_SIZE)]),
        allow_empty=False,
        max_length=5,          
    )
    page = serializers.PrimaryKeyRelatedField(queryset=Page.objects.all(), required=False, allow_null=True)


class SiteVideoListQuerySerializer(serializers.Serializer):
    """
    Validate query parameters for filtering site videos by page UUID.
    """

    page = serializers.UUIDField(required=False)


class SiteVideoOutputSerializer(VideoOutputSerializer):
    """
    Serialize site video data for API responses.

    Extends the base video output with the associated page field.
    """

    class Meta(VideoOutputSerializer.Meta):
        """
        Extend the base video output fields with the page field.
        """

        fields = VideoOutputSerializer.Meta.fields + ["page"]
        read_only_fields = fields

class SiteVideoUpdateInputSerializer(serializers.Serializer):
    """
    Validate input data for updating a site video.

    Supports replacing the video file and updating its title
    or poster image.
    """
    
    file = serializers.FileField( required=False, validators=[video_validator, validate_max_size(MAX_VIDEO_SIZE)])
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    poster = serializers.ImageField(required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])