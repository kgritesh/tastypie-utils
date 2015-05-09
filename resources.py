from functools import update_wrapper, wraps
from tastypie.exceptions import ImmediateHttpResponse
from tastypie.resources import ModelResource


class ModelResourceUtils(ModelResource):

    @classmethod
    def get_fields(cls, fields=None, excludes=None):
        """
        This allows using a custom meta class option `list_exclude_fields` using
        which you can exclude certains fields only from list view, but still
        include them in detail view.
        """

        final_fields = super(ModelResource, cls).get_fields(fields=fields,
                                                            excludes=excludes)

        if getattr(cls._meta, 'list_exclude_fields', None):
            for field_name in final_fields:
                if field_name in cls._meta.list_exclude_fields:
                    final_fields[field_name].use_in = "detail"

        return final_fields

    def wrap_view(self, view):
        """
        Ensure that the decorated function looks like the original view function
        using update_wrapper from the functools package
        """

        wrapper = super(ModelResourceUtils, self).wrap_view(view)
        return update_wrapper(wrapper, getattr(self, view))

    def dehydrate(self, bundle):
        """
        You can restrict the api response to send only certain fields by
        using include_fields/exclude_fields query parameters.
        """

        include_fields = bundle.request.GET.get('include_fields', None)
        exclude_fields = bundle.request.GET.get('exclude_fields', [])

        if not exclude_fields and not include_fields:
            return bundle

        else:
            if not include_fields:
                exclude_fields = exclude_fields.split(",")
                include_fields = set(bundle.data.keys())\
                    .difference(exclude_fields)
            else:
                include_fields = include_fields.split(",")

            bundle.data = {k: bundle.data[k] for k in include_fields}

            return bundle

    def alter_list_data_to_serialize(self, request, data):
        """
        Restrict the api response to only contain the metadata by using
        querystring meta_only
        """

        if request.GET.get('meta_only'):
            return {'meta': data['meta']}
        return data

    @staticmethod
    def get_view_name(request):
        return request.resolver_match.url_name

    def get_model_name(self):
        return self._meta.queryset.model.__name__

    def get_app_label(self):
        return self._meta.queryset.model._meta.app_label

    def get_filters(self, request, **kwargs):
        filters = {}
        kwargs = self.remove_api_resource_names(kwargs)
        if hasattr(request, 'GET'):
            # Grab a mutable copy.
            filters = request.GET.copy()

        filters.update(kwargs)
        return self.build_filters(filters=filters)

    def paginate(self, request, objects):
        """
        Allow custom api's to use paginator defined for the resource
        """
        paginator = self._meta.paginator_class(request.GET, objects,
                                               resource_uri=self.get_resource_uri(),
                                               limit=self._meta.limit,
                                               max_limit=self._meta.max_limit,
                                               collection_name=self._meta.collection_name)
        to_be_serialized = paginator.page()
        return to_be_serialized



class MultipartResource(object):

    def deserialize(self, request, data, format=None):

        if not format:
            format = request.META.get('CONTENT_TYPE', 'application/json')

        if format == 'application/x-www-form-urlencoded':
            return request.POST

        if format.startswith('multipart/form-data'):
            multipart_data = request.POST.copy()
            multipart_data.update(request.FILES)
            return multipart_data

        return super(MultipartResource, self).deserialize(request, data, format)

    def put_detail(self, request, **kwargs):
        if request.META.get('CONTENT_TYPE', '').startswith('multipart/form-data') and not hasattr(request, '_body'):
            request._body = ''
        return super(MultipartResource, self).put_detail(request, **kwargs)

    def patch_detail(self, request, **kwargs):
        if request.META.get('CONTENT_TYPE', '').startswith('multipart/form-data') and not hasattr(request, '_body'):
            request._body = ''
        return super(MultipartResource, self).patch_detail(request, **kwargs)


def authorize_api(resource, allowed_methods, custom_auth=None):
    """
    Decorator to be used with custom api views to perform method_check,
    throttle check and authentication.
    """

    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            resource.method_check(request, allowed_methods)
            resource.throttle_check(request)
            resource_auth = resource._meta.authentication
            if custom_auth:
                resource._meta.authentication = custom_auth

            try:
                resource.is_authenticated(request)
            except ImmediateHttpResponse, ex:
                return ex.response
            finally:
                resource._meta.authentication = resource_auth
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return _decorator