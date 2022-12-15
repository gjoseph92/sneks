from __future__ import annotations

import inspect
from inspect import Signature
from typing import Callable

from sneks.wraps_args import wraps_args


def target(x: int, y: float, z: bool = True) -> list[str]:
    "target"
    ...


@wraps_args(target)
def wrapper(**kwargs) -> str:
    "wrapper"
    ...


# Type assertion
_: Callable[[int, float, bool], str] = wrapper


def test_wraps_args():
    assert target.__doc__ == "target"
    assert wrapper.__doc__ == "wrapper"

    target_sig = inspect.signature(target)
    wrapper_sig = inspect.signature(wrapper)

    assert wrapper_sig.return_annotation == "str"

    assert wrapper_sig.replace(return_annotation=Signature.empty) == target_sig.replace(
        return_annotation=Signature.empty
    )
