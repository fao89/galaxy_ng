
from unittest import mock
from unittest.mock import MagicMock

from galaxy_ng.app.renderers import CustomBrowsableAPIRenderer


def test_show_form_for_method_superuser():
    renderer = CustomBrowsableAPIRenderer()
    request = MagicMock()
    request.user.is_superuser = True
    view = MagicMock()
    method = 'POST'
    obj = None

    with mock.patch(
        'rest_framework.renderers.BrowsableAPIRenderer.show_form_for_method',
        return_value=True
    ) as super_mock:
        result = renderer.show_form_for_method(view, method, request, obj)
        assert result is True
        super_mock.assert_called_once_with(view, method, request, obj)


def test_show_form_for_method_not_superuser():
    renderer = CustomBrowsableAPIRenderer()
    request = MagicMock()
    request.user.is_superuser = False
    view = MagicMock()
    method = 'POST'
    obj = None

    with mock.patch(
        'rest_framework.renderers.BrowsableAPIRenderer.show_form_for_method'
    ) as super_mock:
        result = renderer.show_form_for_method(view, method, request, obj)
        assert result is False
        super_mock.assert_not_called()
