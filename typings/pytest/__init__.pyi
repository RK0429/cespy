"""Type stubs for the parts of pytest used in cespy's test suite."""

from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any, NoReturn, Protocol, TypeVar, overload

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_E = TypeVar("_E", bound=BaseException)


class Config:
    def addinivalue_line(self, name: str, line: str, /) -> None: ...

    def getoption(self, name: str, default: Any = ..., /) -> Any: ...


class Item:  # pragma: no cover - stub only
    keywords: dict[str, Any]

    def add_marker(self, marker: Any, /) -> None: ...


class _ApproxScalar(Protocol):
    def __eq__(self, other: object, /) -> bool: ...

    def __float__(self) -> float: ...


@overload
def approx(
    expected: float | complex,
    *,
    rel: float | None = ...,
    abs: float | None = ...,
    nan_ok: bool = ...,
) -> _ApproxScalar: ...


@overload
def approx(
    expected: Iterable[float | complex],
    *,
    rel: float | None = ...,
    abs: float | None = ...,
    nan_ok: bool = ...,
) -> list[_ApproxScalar]: ...


@overload
def approx(
    expected: Mapping[str, float | complex],
    *,
    rel: float | None = ...,
    abs: float | None = ...,
    nan_ok: bool = ...,
) -> dict[str, _ApproxScalar]: ...


@overload
def fixture(function: Callable[..., _T], /, *args: Any, **kwargs: Any) -> Callable[..., _T]: ...


@overload
def fixture(
    function: None = ...,
    /,
    *args: Any,
    **kwargs: Any,
) -> Callable[[Callable[..., _T]], Callable[..., _T]]: ...


class _MarkDecorator(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

    def __getattr__(self, name: str, /) -> _MarkDecorator: ...


mark: _MarkDecorator


class CaptureFixture(Protocol[_T_co]):
    def readouterr(self) -> tuple[str, str]: ...

    @property
    def text(self) -> str: ...


@overload
def raises(
    expected_exception: type[_E],
    match: str | None = ...,
) -> AbstractContextManager[_E]: ...


@overload
def raises(
    expected_exception: tuple[type[BaseException], ...],
    match: str | None = ...,
) -> AbstractContextManager[BaseException]: ...


def skip(msg: str, /) -> None: ...


def fail(msg: str = ..., *, pytrace: bool = ...) -> NoReturn: ...


def main(args: Sequence[str] | None = None, /) -> int: ...
