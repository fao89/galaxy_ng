
from django.test import RequestFactory, override_settings
from galaxy_ng.app.views import PulpAPIRedirectView


@override_settings(API_ROOT='/api/galaxy/pulp/')
def test_pulp_api_redirect_view_no_query():
    factory = RequestFactory()
    request = factory.get('/v3/foo')
    view = PulpAPIRedirectView.as_view()
    response = view(request, api_path='v3/foo')
    assert response.status_code == 308
    assert response.url == '/api/galaxy/pulp/api/v3/foo/'


@override_settings(API_ROOT='/api/galaxy/pulp/')
def test_pulp_api_redirect_view_with_query():
    factory = RequestFactory()
    request = factory.get('/v3/foo', {'bar': 'baz'})
    view = PulpAPIRedirectView.as_view()
    response = view(request, api_path='v3/foo')
    assert response.status_code == 308
    assert response.url == '/api/galaxy/pulp/api/v3/foo/?bar=baz'
