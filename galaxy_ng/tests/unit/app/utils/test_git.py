
from unittest import mock

from galaxy_ng.app.utils import git


@mock.patch('subprocess.run')
def test_get_tag_commit_date(mock_run):
    mock_process = mock.Mock()
    mock_process.stdout = b'2022-06-07 22:18:41 +0000\n'
    mock_run.return_value = mock_process

    commit_date = git.get_tag_commit_date('https://github.com/ansible/ansible', 'v2.9.0')

    assert commit_date == '2022-06-07T22:18:41'
    mock_run.assert_called_with(
        "git log -1 --format='%ci'",
        shell=True,
        cwd=mock.ANY,
        stdout=mock.PIPE
    )


@mock.patch('subprocess.run')
def test_get_tag_commit_hash(mock_run):
    mock_process = mock.Mock()
    mock_process.stdout = b'f4d4f4d4f4d4f4d4f4d4f4d4f4d4f4d4f4d4f4d4\n'
    mock_run.return_value = mock_process

    commit_hash = git.get_tag_commit_hash('https://github.com/ansible/ansible', 'v2.9.0')

    assert commit_hash == 'f4d4f4d4f4d4f4d4f4d4f4d4f4d4f4d4f4d4f4d4'
    mock_run.assert_called_with(
        "git log -1 --format='%H'",
        shell=True,
        cwd=mock.ANY,
        stdout=mock.PIPE
    )
