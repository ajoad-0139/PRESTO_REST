from rest_framework import serializers

from sites.models import Page
from sites.validators import html_validator, css_validator, js_validator, image_validator, validate_max_size
from sites.utils.constraints import MAX_HTML_SIZE, MAX_CSS_SIZE, MAX_JS_SIZE, MAX_THUMBNAIL_SIZE


class PageCreateInputSerializer(serializers.ModelSerializer):
    """
    Validate and deserialize input data for creating a page.

    Validates page metadata and uploaded HTML, CSS, JavaScript,
    and Open Graph image files.
    """

    class Meta:
        """
        Configure the Page model and accepted input fields.
        """

        model = Page
        fields = [
            "title", "page_type", "canonical_url",
            "meta_title", "meta_description", "og_title", "og_description",
            "og_image", "no_index", "html_file", "css_file", "js_file",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    canonical_url = serializers.CharField(required=False, allow_blank=True, max_length=500)

    html_file = serializers.FileField(required=True, allow_null=False,validators=[html_validator, validate_max_size(MAX_HTML_SIZE)])
    css_file = serializers.FileField(required=True, allow_null=False,validators=[css_validator, validate_max_size(MAX_CSS_SIZE)])
    js_file = serializers.FileField(required=False, allow_null=True, validators=[js_validator, validate_max_size(MAX_JS_SIZE)])
    og_image = serializers.FileField(required=False, allow_null=True, validators=[image_validator, validate_max_size(MAX_THUMBNAIL_SIZE)])
    no_index = serializers.BooleanField(default=False)

    def validate_title(self, value):
        """
        Strip whitespace from the title and ensure it has at least
        two characters.

        Args:
            value: Page title provided in the request.

        Returns:
            str: Cleaned page title.

        Raises:
            serializers.ValidationError: If the title has fewer than
                two characters.
        """

        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Title must be at least 2 characters.")
        return value

    def validate_page_type(self, value):
        """
        Normalize the page type by stripping whitespace and
        converting it to lowercase.

        Args:
            value: Page type provided in the request.

        Returns:
            str: Normalized page type.
        """

        return value.strip().lower()


class PageListQuerySerializer(serializers.Serializer):
    """
    Validate query parameters used to filter and search pages.

    Supports filtering by page type and searching by a text query.
    """

    page_type = serializers.CharField(required=False)
    search = serializers.CharField(required=False)


class PageOutputSerializer(serializers.ModelSerializer):
    """
    Serialize page data for API responses.

    Returns page metadata, SEO fields, uploaded assets, associated
    site information, and creation and update timestamps.
    """

    class Meta:
        """
        Configure the Page model and read-only output fields.
        """
        
        model = Page
        fields = [
            "id", "title", "slug", "page_type", "canonical_url",
            "meta_title", "meta_description", "og_title", "og_description",
            "og_image", "no_index", "html_file", "css_file", "js_file",
            "site", "created_at", "updated_at",
        ]
        read_only_fields = fields