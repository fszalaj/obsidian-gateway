import pytest
from fastmcp.exceptions import ToolError

from gateway import acl
from gateway.tools import _expected_to_tool_error


def test_expected_failures_become_toolerror():
    for exc in (
        FileNotFoundError("not_found: x"),
        FileExistsError("exists: x"),
        ValueError("too_large: x"),
        ValueError("bad_message: empty commit message"),
        ValueError("frontmatter_unparseable: x"),
        PermissionError("path_escape: x"),
        acl.AccessDenied("vault_forbidden: x"),
    ):
        @_expected_to_tool_error
        def f(e=exc):
            raise e

        with pytest.raises(ToolError):
            f()


def test_unexpected_failures_pass_through_unmasked():
    @_expected_to_tool_error
    def f():
        raise PermissionError("Operation not permitted: /etc/secret")  # no expected prefix

    with pytest.raises(PermissionError):
        f()


def test_toolerror_is_not_rewrapped():
    @_expected_to_tool_error
    def f():
        raise ToolError("already a tool error")

    with pytest.raises(ToolError):
        f()
