from django.db import transaction, IntegrityError
from sites.models import Theme
from sites.exceptions import ThemeAlreadyExists

class ThemeService :
    @classmethod
    @transaction.atomic
    def create(cls, *, name: str, thumbnail, header,footer, body, 
               css_file, language: str = "en", js_file=None, slug: str = "",
               description: str = "", is_active: bool = True, created_by) -> Theme:
        
        themes = Theme.objects.filter(name__iexact=name, language=language)
        if themes.exists():
            ThemeAlreadyExists()

        theme = Theme(
            name=name, slug=slug, description=description, is_active=is_active,
            language=language, thumbnail=thumbnail, header=header, footer=footer,
            body=body, css_file=css_file, js_file=js_file, created_by=created_by
        )
        
        theme.save()

        return theme