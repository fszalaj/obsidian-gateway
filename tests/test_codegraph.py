"""codegraph extractor tests - Python (ast) + Ansible (yaml), no tree-sitter needed."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("networkx")

from gateway.codegraph import build_graph
from gateway.codegraph import extract_ansible, extract_python


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _ansible_repo(root):
    _write(root / "filter_plugins/my_filters.py",
           "def build_body(x):\n    return x\n\n"
           "class FilterModule:\n    def filters(self):\n        return {'build_body': build_body}\n")
    _write(root / "roles/web/meta/main.yml", "dependencies:\n  - role: common\n")
    _write(root / "roles/common/meta/main.yml", "dependencies: []\n")
    _write(root / "roles/web/tasks/main.yml",
           "- name: build the body\n  set_fact:\n    body: \"{{ data | build_body }}\"\n"
           "- name: do more\n  include_tasks: more.yml\n"
           "- name: poke\n  command: echo hi\n  notify: restart web\n")
    _write(root / "roles/web/tasks/more.yml", "- name: more\n  debug: msg=hi\n")
    _write(root / "roles/web/handlers/main.yml", "- name: restart web\n  debug: msg=restart\n")
    _write(root / "playbook_site.yml", "- hosts: all\n  roles:\n    - web\n")


def test_ansible_extracts_roles_filters_and_calls_filter(tmp_path):
    _ansible_repo(tmp_path)
    frag = extract_ansible.extract(tmp_path)
    rels = {(e["source"], e["relation"], e["target"]) for e in frag["edges"]}
    ids = {n["id"] for n in frag["nodes"]}
    assert "role:web" in ids and "role:common" in ids
    assert "filter:build_body" in ids
    # the differentiator: an Ansible task -> Python filter edge
    assert any(r == "calls_filter" and t == "filter:build_body" for _, r, t in rels)
    assert any(r == "role_depends_on" and t == "role:common" for _, r, t in rels)
    assert any(r == "uses_role" and t == "role:web" for _, r, t in rels)
    assert any(r == "include_tasks" for _, r, _ in rels)
    assert any(r == "notifies" and t == "handler:restart web" for _, r, t in rels)
    assert any(r == "implemented_by" for _, r, _ in rels)


def test_python_extractor(tmp_path):
    p = tmp_path / "m.py"
    _write(p, "import os\n\ndef helper():\n    return 1\n\ndef main():\n    return helper()\n\nclass C:\n    pass\n")
    frag = extract_python.extract(p, "m.py")
    ids = {n["id"] for n in frag["nodes"]}
    assert "pyfunc:m.py:helper" in ids and "pyclass:m.py:C" in ids and "module:m.py" in ids
    rels = {(e["source"], e["relation"], e["target"]) for e in frag["edges"]}
    assert ("pyfunc:m.py:main", "calls", "pyfunc:m.py:helper") in rels
    assert any(r == "imports" for _, r, _ in rels)


def test_build_graph_roundtrip(tmp_path):
    _ansible_repo(tmp_path)
    _write(tmp_path / "lib/util.py", "def f():\n    return 2\n")
    data = build_graph(tmp_path)
    assert data["graph"]["schema_version"] == 1
    assert data["graph"]["node_count"] > 0
    assert data["graph"]["edge_count"] > 0
    # node-link shape is JSON-serialisable and has links
    s = json.dumps(data)
    assert "links" in data and isinstance(data["links"], list)
    assert any(n["id"] == "pyfunc:lib/util.py:f" for n in data["nodes"])
    # communities baked onto nodes
    assert all("id" in n for n in data["nodes"])
    assert len(s) > 100
