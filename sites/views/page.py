
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from sites.responses import success_response
from sites.services.page import PageService
from sites.serializers.page import (
    PageCreateInputSerializer, PageListQuerySerializer, PageOutputSerializer,
)

class PageList(APIView):
    """
    GET  /sites/{site_id}/pages/  -> list pages of a site
    POST /sites/{site_id}/pages/  -> create a page
    """
    permission_classes = [IsAuthenticated]

    services = PageService
    create_input_serializer = PageCreateInputSerializer
    list_query_serializer = PageListQuerySerializer
    output_serializer = PageOutputSerializer
    
    def get(self, request, site_id):
        query = self.list_query_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        pages = self.services.list(site_id=site_id, **query.validated_data)

        return success_response(
            self.output_serializer(pages, many=True).data,
            "Pages retrieved",
        )
 
    def post(self, request, site_id):
        serializer = self.create_input_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        page = self.services.create(site_id=site_id, user=request.user, **serializer.validated_data)

        return success_response(
            self.output_serializer(page).data,
            "Page created",
            status.HTTP_201_CREATED,
        )
 
class PageDetail(APIView):
    """
    GET    /sites/{site_id}/pages/{page_id}/  -> page detail
    PATCH  /sites/{site_id}/pages/{page_id}/  -> update page
    DELETE /sites/{site_id}/pages/{page_id}/  -> delete page
    """
    permission_classes = [IsAuthenticated]

    services = PageService
    output_serializer = PageOutputSerializer
    update_input_serializer = PageCreateInputSerializer

    def get(self, request, site_id, page_id):
        page = self.services.get(site_id=site_id, page_id=page_id)

        return success_response(
            self.output_serializer(page).data,
            "Page retrieved",
        )
 
    def patch(self, request, site_id, page_id):
        serializer = self.update_input_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        page = self.services.update(site_id=site_id, page_id=page_id, user=request.user, **serializer.validated_data)

        return success_response(
            self.output_serializer(page).data,
            "Page updated",
        )
 
    def delete(self, request, site_id, page_id):
        self.services.delete(site_id=site_id, page_id=page_id, user=request.user)
        return success_response(message="Page deleted")
 