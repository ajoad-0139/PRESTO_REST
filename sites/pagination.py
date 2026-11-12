"""Define the default pagination configuration for API responses."""

from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Provide page-number pagination with configurable page sizes."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_data(self, items):
        """Return paginated items with pagination metadata."""
        return {
            "items": items,
            "pagination": {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "total_pages": self.page.paginator.num_pages,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            },
        }