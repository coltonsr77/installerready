import types
from unittest.mock import Mock

import pytest

from installerready import InstallerReady


def make_instance():
    # Create instance without calling __init__ to avoid Tk window creation
    inst = InstallerReady.__new__(InstallerReady)
    return inst


def test_get_repo_name():
    inst = make_instance()
    assert inst.get_repo_name('https://github.com/owner/repo') == 'repo'
    assert inst.get_repo_name('git@github.com:owner/repo.git') == 'repo'
    assert inst.get_repo_name('https://github.com/owner/repo/') == 'repo'


def test_parse_owner_repo():
    inst = make_instance()
    owner, repo = inst.parse_owner_repo('https://github.com/owner/repo')
    assert owner == 'owner' and repo == 'repo'
    owner, repo = inst.parse_owner_repo('git@github.com:owner/repo.git')
    assert owner == 'owner' and repo == 'repo'


def test_get_default_branch(monkeypatch):
    inst = make_instance()

    mock_resp = Mock()
    mock_resp.json.return_value = {'default_branch': 'main'}

    monkeypatch.setattr(inst, 'api_request', lambda method, url, **kwargs: mock_resp)

    branch = inst.get_default_branch('https://github.com/owner/repo')
    assert branch == 'main'
