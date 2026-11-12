
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from sites.responses import success_response
from sites.services.page import PageService
from sites.serializers.page import (
    PageCreateInputSerializer, PageListQuerySerializer, PageOutputSerializer,
)

class PageList(APIView):
    """Handle listing and creating pages for a site."""

    permission_classes = [IsAuthenticated]

    services = PageService
    create_input_serializer = PageCreateInputSerializer
    list_query_serializer = PageListQuerySerializer
    output_serializer = PageOutputSerializer
    
    def get(self, request, site_id):
        """Retrieve pages belonging to a site.

        Args:
            request: HTTP request containing query parameters.
            site_id: ID of the site.

        Returns:
            Response containing serialized pages.
        """


        query = self.list_query_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        pages = self.services.list(site_id=site_id, **query.validated_data)

        return success_response(
            self.output_serializer(pages, many=True).data,
            "Pages retrieved",
        )
 
    def post(self, request, site_id):
        """Create a new page for a site.

        Args:
            request: HTTP request containing page data.
            site_id: ID of the site.

        Returns:
            Response containing the created page.
        """

        serializer = self.create_input_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        page = self.services.create(site_id=site_id, user=request.user, **serializer.validated_data)

        return success_response(
            self.output_serializer(page).data,
            "Page created",
            status.HTTP_201_CREATED,
        )
 
class PageDetail(APIView):
    """Handle retrieving, updating, and deleting a site page."""

    permission_classes = [IsAuthenticated]

    services = PageService
    output_serializer = PageOutputSerializer
    update_input_serializer = PageCreateInputSerializer

    def get(self, request, site_id, page_id):
        """Retrieve a specific page.

        Args:
            request: HTTP request.
            site_id: ID of the site.
            page_id: ID of the page.

        Returns:
            Response containing the serialized page.
        """


        page = self.services.get(site_id=site_id, page_id=page_id)

        return success_response(
            self.output_serializer(page).data,
            "Page retrieved",
        )
 
    def patch(self, request, site_id, page_id):
        """Partially update an existing page.

        Args:
            request: HTTP request containing fields to update.
            site_id: ID of the site.
            page_id: ID of the page.

        Returns:
            Response containing the updated page.
        """


        serializer = self.update_input_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        page = self.services.update(site_id=site_id, page_id=page_id, user=request.user, **serializer.validated_data)

        return success_response(
            self.output_serializer(page).data,
            "Page updated",
        )
 
    def delete(self, request, site_id, page_id):
        """Delete a page from a site.

        Args:
            request: HTTP request.
            site_id: ID of the site.
            page_id: ID of the page.

        Returns:
            Response confirming deletion.
        """

        
        self.services.delete(site_id=site_id, page_id=page_id, user=request.user)
        return success_response(message="Page deleted")
 