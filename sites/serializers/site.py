from rest_framework import serializers

from sites.models import Site, Theme, Page
from sites.validators import image_validator, validate_max_size, video_validator
from sites.serializers.asset import ImageOutputSerializer, VideoOutputSerializer
from sites.constraints import MAX_THUMBNAIL_SIZE, SUPPORTED_LANGUAGES, MAX_IMAGE_SIZE, MAX_VIDEO_SIZE


class SiteCreateInputSerializer(serializers.ModelSerializer):
    class Meta:
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

    def validate_published_domain(self, value):
        value = (value or "").strip().lower()
        return value or None


class SiteListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Site.Status.choices, required=False)
    language = serializers.CharField(required=False)
    search = serializers.CharField(required=False)


class SiteOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = [
            "id", "name", "slug", "description", "language", "status",
            "published_domain", "favicon", "meta_description", "og_image", "no_index",
            "header", "footer", "body", "css_file", "js_file",
            "theme", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = fields


class SiteUpdateInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = [
            "name", "description", "language", "status", "published_domain",
            "favicon", "meta_description", "og_image", "no_index",
        ]

    favicon = serializers.ImageField( required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])
    og_image = serializers.FileField( required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])

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

    def validate_published_domain(self, value):
        value = (value or "").strip().lower()
        return value or None


class SiteImageCreateInputSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.ImageField(validators=[image_validator, validate_max_size(MAX_IMAGE_SIZE)]),
        allow_empty=False, 
        max_length=10,
    )
    alt_text = serializers.CharField(max_length=255, required=False, allow_blank=True)
    page = serializers.PrimaryKeyRelatedField(queryset=Page.objects.all(), required=False, allow_null=True)


class SiteImageListQuerySerializer(serializers.Serializer):
    page = serializers.UUIDField(required=False)


class SiteImageOutputSerializer(ImageOutputSerializer):
    class Meta(ImageOutputSerializer.Meta):
        fields = ImageOutputSerializer.Meta.fields + ["page"]
        read_only_fields = fields

class SiteImageUpdateInputSerializer(serializers.Serializer):
    file = serializers.ImageField(
        required=False,
        validators=[image_validator, validate_max_size(MAX_IMAGE_SIZE)],
    )
    alt_text = serializers.CharField(max_length=255, required=False, allow_blank=True)

class SiteVideoCreateInputSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(validators=[video_validator, validate_max_size(MAX_VIDEO_SIZE)]),
        allow_empty=False,
        max_length=5,          
    )
    page = serializers.PrimaryKeyRelatedField(queryset=Page.objects.all(), required=False, allow_null=True)


class SiteVideoListQuerySerializer(serializers.Serializer):
    page = serializers.UUIDField(required=False)


class SiteVideoOutputSerializer(VideoOutputSerializer):
    class Meta(VideoOutputSerializer.Meta):
        fields = VideoOutputSerializer.Meta.fields + ["page"]
        read_only_fields = fields

class SiteVideoUpdateInputSerializer(serializers.Serializer):
    file = serializers.FileField( required=False, validators=[video_validator, validate_max_size(MAX_VIDEO_SIZE)])
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    poster = serializers.ImageField(required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])