from typing import Any, Callable, TypeVar, cast

from typing_extensions import ParamSpec

P = ParamSpec("P")
T = TypeVar("T")


def wraps_args(
    wrapped: Callable[P, Any]
) -> Callable[[Callable[..., T]], Callable[P, T]]:
    def inner(wrapper: Callable[..., T]) -> Callable[P, T]:
        import inspect

        wrapper.__dict__["__signature__"] = inspect.signature(wrapped).replace(
            return_annotation=inspect.signature(wrapper).return_annotation
        )
        return cast(Callable[P, T], wrapper)

    return inner
