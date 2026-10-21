import sys
from pathlib import Path

import pytest
from textual.widgets import Input
from textual_autocomplete import TargetState

from rovr.app import Application
from rovr.functions.cwd import getcwd
from rovr.functions.path import normalise
from rovr.navigation_widgets.path_input import (
    PathAutoCompleteInput,
    PathInput,
    get_path_segments,
    get_segment_at,
    should_exclude_hidden,
)


def test_should_exclude_hidden_empty() -> None:
    assert not should_exclude_hidden("")


def test_should_exclude_hidden_dot_terminal() -> None:
    """User typed '.' alone or as last component → show dotfiles."""
    assert not should_exclude_hidden(".")
    assert not should_exclude_hidden("/home/.")


def test_should_exclude_hidden_double_dot_filters() -> None:
    """.. represents navigation, so it MUST filter."""
    assert should_exclude_hidden("..")
    assert should_exclude_hidden("/home/..")
    assert should_exclude_hidden("C:\\Windows\\..")


def test_should_exclude_hidden_dotfile_no_filter() -> None:
    assert not should_exclude_hidden("/foo/.config")
    assert should_exclude_hidden("/foo/.hidden_dir/")
    assert not should_exclude_hidden("/home/...cache")


def test_should_exclude_hidden_visible_filters() -> None:
    assert should_exclude_hidden("/home")
    assert should_exclude_hidden("/home/")
    assert should_exclude_hidden("/home/projects")
    assert should_exclude_hidden("C:/Users/Me/Documents")


@pytest.mark.skipif(sys.platform != "win32", reason="Need to be on Windows")
def test_should_exclude_hidden_backslash_separator() -> None:
    """Backslashes should work as separators too."""
    assert not should_exclude_hidden("C:\\foo\\.git")


def test_should_exclude_hidden_trailing_slashes_no_separator() -> None:
    """Path with trailing slashes but no final component still filters
    (same behaviour as the original implementation)."""
    assert should_exclude_hidden("/home/foo///")


@pytest.mark.skipif(sys.platform != "win32", reason="Need to be on Windows")
def test_search_string_accepts_backslash_separator() -> None:
    autocomplete = PathAutoCompleteInput(Input())
    value = "C:/Users/example\\"

    assert autocomplete.get_search_string(TargetState(value, len(value))) == ""


def test_get_path_segments_splits_every_component() -> None:
    assert get_path_segments("/home/denys/Documents/Old/") == [
        ("home", "/home", 0, 5),
        ("denys", "/home/denys", 6, 11),
        ("Documents", "/home/denys/Documents", 12, 21),
        ("Old", "/home/denys/Documents/Old", 22, 25),
    ]


def test_get_path_segments_keeps_spaces_and_accents() -> None:
    path_str = "/home/denys/Currículos e Entrevistas/Old/"
    assert [(label, target) for label, target, _, _ in get_path_segments(path_str)] == [
        ("home", "/home"),
        ("denys", "/home/denys"),
        ("Currículos e Entrevistas", "/home/denys/Currículos e Entrevistas"),
        ("Old", "/home/denys/Currículos e Entrevistas/Old"),
    ]


def test_get_path_segments_handles_trailing_separator() -> None:
    assert get_path_segments("/home/denys/") == get_path_segments("/home/denys")


@pytest.mark.parametrize("path_str", ["/", "", "home", "."])
def test_get_path_segments_without_anything_to_click(path_str: str) -> None:
    assert get_path_segments(path_str) == []


def test_get_path_segments_at_root_level() -> None:
    assert get_path_segments("/home") == [("home", "/home", 0, 5)]


def test_get_segment_at_maps_index_to_directory() -> None:
    segments = get_path_segments("/home/denys/Documents/")
    assert get_segment_at(segments, 0) == "/home"
    assert get_segment_at(segments, 4) == "/home"
    assert get_segment_at(segments, 6) == "/home/denys"
    assert get_segment_at(segments, 18) == "/home/denys/Documents"


def test_get_segment_at_ignores_separators_and_padding() -> None:
    segments = get_path_segments("/home/denys/")
    assert get_segment_at(segments, 5) is None
    assert get_segment_at(segments, 40) is None
    assert get_segment_at(segments, -1) is None


@pytest.mark.asyncio
async def test_clicking_segment_navigates_to_it(tmp_path: Path) -> None:
    target = tmp_path / "A" / "B" / "C"
    target.mkdir(parents=True)
    app = Application(startup_path=target.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        path_input = app.query_one("#path_switcher", PathInput)
        char_x = _char_x(path_input, path_input.value.index("/A/") + 1)
        await pilot.click(offset=(path_input.region.x + char_x, path_input.region.y))
        await pilot.pause()
        await pilot.pause()
        assert getcwd() == (tmp_path / "A").as_posix() or normalise(
            getcwd()
        ) == normalise((tmp_path / "A").as_posix())


@pytest.mark.asyncio
async def test_clicking_empty_space_only_focuses(tmp_path: Path) -> None:
    (tmp_path / "A").mkdir()
    app = Application(startup_path=(tmp_path / "A").as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        path_input = app.query_one("#path_switcher", PathInput)
        char_x = _char_x(path_input, len(path_input.value) + 10)
        await pilot.click(offset=(path_input.region.x + char_x, path_input.region.y))
        await pilot.pause()
        assert normalise(getcwd()) == normalise((tmp_path / "A").as_posix())
        assert path_input.has_focus


@pytest.mark.asyncio
async def test_toggle_binding_puts_cursor_at_end(tmp_path: Path) -> None:
    app = Application(startup_path=tmp_path.as_posix())
    async with app.run_test(size=(143, 37)) as pilot:
        await pilot.pause()
        path_input = app.query_one("#path_switcher", PathInput)
        await pilot.press("ctrl+l")
        await pilot.pause()
        assert path_input.has_focus
        assert path_input.cursor_position == len(path_input.value)


def _char_x(path_input: PathInput, index: int) -> int:
    return (
        path_input.content_region.x
        - path_input.region.x
        + index
        - path_input.scroll_offset.x
    )
