from sites.models import Theme
from rest_framework import serializers
from sites.validators import validate_max_size, image_validator, html_validator, css_validator, js_validator
from sites.constraints import MAX_CSS_SIZE, MAX_HTML_SIZE, MAX_JS_SIZE, MAX_THUMBNAIL_SIZE, SUPPORTED_LANGUAGES


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