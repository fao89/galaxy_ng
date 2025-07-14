from unittest import mock
import datetime

from galaxy_ng.app.utils import roles


@mock.patch('subprocess.run')
def test_get_path_git_root(mock_run):
    mock_process = mock.Mock()
    mock_process.stdout = b'/tmp/test_repo\n'
    mock_run.return_value = mock_process

    root = roles.get_path_git_root('/tmp/test_repo/tasks')
    assert root == '/tmp/test_repo'


@mock.patch('subprocess.run')
def test_get_path_head_date(mock_run):
    mock_process = mock.Mock()
    mock_process.stdout = b'2021-10-31 00:03:43 -0500\n'
    mock_run.return_value = mock_process

    date = roles.get_path_head_date('/tmp/test_repo')
    assert isinstance(date, datetime.datetime)


@mock.patch('subprocess.run')
def test_get_path_role_repository(mock_run):
    mock_process = mock.Mock()
    mock_process.stdout = b'https://github.com/ansible/ansible-role-test.git\n'
    mock_run.return_value = mock_process

    repo = roles.get_path_role_repository('/tmp/test_repo')
    assert repo == 'https://github.com/ansible/ansible-role-test.git'


@mock.patch('builtins.open', new_callable=mock.mock_open,
            read_data='galaxy_info: { role_name: test_role }')
def test_get_path_role_meta(mock_open):
    meta = roles.get_path_role_meta('/tmp/test_repo')
    assert meta['galaxy_info']['role_name'] == 'test_role'


@mock.patch('galaxy_ng.app.utils.roles.get_path_galaxy_key', return_value='test_name')
def test_get_path_role_name_from_galaxy_yml(mock_get_key):
    name = roles.get_path_role_name('/tmp/test_repo')
    assert name == 'test_name'


@mock.patch('galaxy_ng.app.utils.roles.get_path_galaxy_key', return_value=None)
@mock.patch('builtins.open', new_callable=mock.mock_open,
            read_data='galaxy_info: { role_name: test_role }')
def test_get_path_role_name_from_meta(mock_open, mock_get_key):
    name = roles.get_path_role_name('/tmp/test_repo')
    assert name == 'test_role'


@mock.patch('galaxy_ng.app.utils.roles.get_path_galaxy_key', return_value=None)
@mock.patch('os.path.exists', return_value=False)
@mock.patch('subprocess.run')
def test_get_path_role_name_from_git(mock_run, mock_exists, mock_get_key):
    mock_process = mock.Mock()
    mock_process.stdout = b'https://github.com/ansible/ansible-role-test.git\n'
    mock_run.return_value = mock_process

    name = roles.get_path_role_name('/tmp/test_repo')
    assert name == 'test'


@mock.patch('galaxy_ng.app.utils.roles.get_path_galaxy_key', return_value='test_namespace')
def test_get_path_role_namespace_from_galaxy_yml(mock_get_key):
    namespace = roles.get_path_role_namespace('/tmp/test_repo')
    assert namespace == 'test_namespace'


@mock.patch('galaxy_ng.app.utils.roles.get_path_galaxy_key', return_value=None)
@mock.patch('subprocess.run')
def test_get_path_role_namespace_from_git(mock_run, mock_get_key):
    mock_process = mock.Mock()
    mock_process.stdout = b'https://github.com/ansible/ansible-role-test.git\n'
    mock_run.return_value = mock_process

    namespace = roles.get_path_role_namespace('/tmp/test_repo')
    assert namespace == 'ansible'


@mock.patch('galaxy_ng.app.utils.roles.get_path_galaxy_key', return_value='1.2.3')
def test_get_path_role_version_from_galaxy_yml(mock_get_key):
    version = roles.get_path_role_version('/tmp/test_repo')
    assert version == '1.2.3'


@mock.patch('galaxy_ng.app.utils.roles.get_path_galaxy_key', return_value=None)
@mock.patch('galaxy_ng.app.utils.roles.get_path_head_date')
def test_get_path_role_version_from_git(mock_get_date, mock_get_key):
    mock_get_date.return_value = datetime.datetime(2022, 1, 1, 12, 0, 0)
    version = roles.get_path_role_version('/tmp/test_repo')
    assert version.startswith('1.0.0')


@mock.patch('glob.glob', return_value=['/tmp/test_repo/tasks'])
def test_path_is_role_true(mock_glob):
    assert roles.path_is_role('/tmp/test_repo') is True


@mock.patch('glob.glob', return_value=['/tmp/test_repo/plugins'])
def test_path_is_role_false(mock_glob):
    assert roles.path_is_role('/tmp/test_repo') is False


@mock.patch('os.path.exists', return_value=False)
@mock.patch('os.makedirs')
@mock.patch('builtins.open', new_callable=mock.mock_open)
def test_make_runtime_yaml(mock_open, mock_makedirs, mock_exists):
    roles.make_runtime_yaml('/tmp/test_repo')
    mock_makedirs.assert_called_once_with('/tmp/test_repo/meta')
    mock_open.assert_called_once_with('/tmp/test_repo/meta/runtime.yml', 'w')


@mock.patch('os.path.exists', return_value=True)
@mock.patch('builtins.open', new_callable=mock.mock_open, read_data='namespace: ansible')
def test_get_path_galaxy_key(mock_open, mock_exists):
    value = roles.get_path_galaxy_key('/tmp/test_repo', 'namespace')
    assert value == 'ansible'


@mock.patch('builtins.open', new_callable=mock.mock_open, read_data='namespace: ansible')
def test_set_path_galaxy_key(mock_open):
    roles.set_path_galaxy_key('/tmp/test_repo', 'name', 'test_role')
    handle = mock_open()
    handle.write.assert_called_once()
