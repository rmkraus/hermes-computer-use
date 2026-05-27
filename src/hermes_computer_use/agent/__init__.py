"""DeepAgent harness for Ubuntu desktop automation."""

__all__ = ["create_computer_use_agent", "get_computer_use_tools"]


def create_computer_use_agent(*args, **kwargs):
    from hermes_computer_use.agent.graph import create_computer_use_agent as _create
    return _create(*args, **kwargs)


def get_computer_use_tools(*args, **kwargs):
    from hermes_computer_use.agent.tools import get_computer_use_tools as _get
    return _get(*args, **kwargs)
