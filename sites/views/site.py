from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from sites.pagination import DefaultPagination
from sites.responses import success_response
from sites.services.site import SiteService
from sites.serializers.site import (SiteCreateInputSerializer, SiteListQuerySerializer, SiteOutputSerializer,
    SiteUpdateInputSerializer)


class SiteList(APIView):
    """
    GET  /sites/  -> list the current user's sites
    POST /sites/  -> create a site
    """
    permission_classes = [IsAuthenticated]

    services = SiteService
    create_input_serializer = SiteCreateInputSerializer
    list_query_serializer = SiteListQuerySerializer
    output_serializer = SiteOutputSerializer
    pagination_class = DefaultPagination
    
    def get(self, request):
        query = self.list_query_serializer(data=request.query_params, partial=True)
        query.is_valid(raise_exception=True)

        sites = self.services.list(user=request.user, **query.validated_data)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(sites, request, view=self)
        items = self.output_serializer(page, many=True).data

        return success_response(paginator.get_paginated_data(items), "Sites retrieved")
 
    def post(self, request):
        serializer = self.create_input_serializer(data=request.data, context={"request": request},)
        serializer.is_valid(raise_exception=True)

        site = self.services.create(**serializer.validated_data)

        return success_response(
            self.output_serializer(site).data,
            "Site created",
            status.HTTP_201_CREATED,
        )
 

 
class SiteDetail(APIView):
    """
    GET    /sites/{site_id}/  -> site detail
    PATCH  /sites/{site_id}/  -> update site
    DELETE /sites/{site_id}/  -> delete site
    """
    permission_classes = [IsAuthenticated]

    services = SiteService
    output_serializer = SiteOutputSerializer
    update_input_serializer = SiteUpdateInputSerializer
    
    def get(self, request, site_id):
        site = self.services.get(site_id=site_id)

        return success_response(
            self.output_serializer(site).data,
            "Site retrieved",
        )
    
    def patch(self, request, site_id):
        site = self.services.get(site_id=site_id)

        serializer = self.update_input_serializer( site, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)

        site = self.services.update(site=site, **serializer.validated_data)

        return success_response(
            self.output_serializer(site).data,
            "Site updated",
        )
 
    def delete(self, request, site_id):
        self.services.delete(site_id=site_id, user=request.user)
        return success_response(message="Site deleted")


class SiteImageList(APIView):
    """
    GET  /sites/{site_id}/images/  -> list site images (?page=<uuid> to filter)
    POST /sites/{site_id}/images/  -> upload a site image
    """

    def get(self, request, site_id):
        pass

    def post(self, request, site_id):
        pass

 
class SiteImageDetail(APIView):
    """
    GET    /sites/{site_id}/images/{image_id}/  -> image detail
    PATCH  /sites/{site_id}/images/{image_id}/  -> update image (alt text, file)
    DELETE /sites/{site_id}/images/{image_id}/  -> delete image
    """
 
    def get(self, request, site_id, image_id):
        pass
 
    def patch(self, request, site_id, image_id):
        pass
 
    def delete(self, request, site_id, image_id):
        pass
 
 
class SiteVideoList(APIView):
    """
    GET  /sites/{site_id}/videos/  -> list site videos (?page=<uuid> to filter)
    POST /sites/{site_id}/videos/  -> upload a site video
    """
 
    def get(self, request, site_id):
        pass
 
    def post(self, request, site_id):
        pass
 
 
class SiteVideoDetail(APIView):
    """
    GET    /sites/{site_id}/videos/{video_id}/  -> video detail
    PATCH  /sites/{site_id}/videos/{video_id}/  -> update video (title, poster, file)
    DELETE /sites/{site_id}/videos/{video_id}/  -> delete video
    """
 
    def get(self, request, site_id, video_id):
        pass
 
    def patch(self, request, site_id, video_id):
        pass
 
    def delete(self, request, site_id, video_id):
        pass