1) Allow restricting fields which an api call return using query parameters (include_fields and exclude_fields)
2) Allow restricting the api to only return metadata using query parameter meta_only
3) A custom mixin that allows tastypie to handle multipart requests
4) Some helper methods to get view name, model name and the app label for the resource
5) Helper method to use tastypie paginator in custom api views
6) A decorator that ensures method check, authentication check and throttle test
   for custom api endpoints.
7) Added a meta option list_exclude_fields which will exclude fields from
list views, but still returning them in detail view
