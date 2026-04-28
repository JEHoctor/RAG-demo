from __future__ import annotations

from enum import Enum
from typing import cast

import pytest
from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.widgets import Checkbox, Input, TabbedContent

from rag_demo.modes.config import ConfigScreen, ConfigWidget, EnumRadioSet, PlaceholderConfigWidget


class _FlatConfig(BaseModel):
    name: str = "Alice"
    active: bool = False


class _EnumOption(Enum):
    FIRST = "first"
    SECOND = "second"


class _EnumConfig(BaseModel):
    choice: _EnumOption = _EnumOption.FIRST


class _WidgetApp(App[None]):
    """Minimal app for mounting a single ConfigWidget under test."""

    def __init__(self, widget: ConfigWidget) -> None:
        super().__init__()
        self._widget = widget

    def compose(self) -> ComposeResult:
        yield self._widget


class _ScreenApp(App[None]):
    """Minimal app for mounting a ConfigScreen under test."""

    async def on_mount(self) -> None:
        await self.push_screen(ConfigScreen())


# --- ConfigWidget ---


async def test_config_widget_str_field_creates_input() -> None:
    """A str field creates an Input pre-populated with the current config value."""
    widget: ConfigWidget[_FlatConfig] = ConfigWidget("test", _FlatConfig(), _FlatConfig, lambda _: None)
    async with _WidgetApp(widget).run_test() as pilot:
        assert pilot.app.query_one(Input).value == "Alice"


async def test_config_widget_bool_field_creates_checkbox() -> None:
    """A bool field creates a Checkbox reflecting the current config value."""
    widget: ConfigWidget[_FlatConfig] = ConfigWidget("test", _FlatConfig(), _FlatConfig, lambda _: None)
    async with _WidgetApp(widget).run_test() as pilot:
        assert pilot.app.query_one(Checkbox).value is False


async def test_config_widget_enum_field_creates_radio_set() -> None:
    """An Enum field creates an EnumRadioSet."""
    widget: ConfigWidget[_EnumConfig] = ConfigWidget("test", _EnumConfig(), _EnumConfig, lambda _: None)
    async with _WidgetApp(widget).run_test() as pilot:
        assert pilot.app.query_one(EnumRadioSet) is not None


async def test_config_widget_collect_config_unchanged() -> None:
    """collect_config with no user interaction returns a config equal to the original."""
    config = _FlatConfig()
    widget: ConfigWidget[_FlatConfig] = ConfigWidget("test", config, _FlatConfig, lambda _: None)
    async with _WidgetApp(widget).run_test():
        result = widget.collect_config()
    assert result == config


async def test_config_widget_collect_config_after_str_change() -> None:
    """Changing an Input value is reflected when collect_config is called."""
    widget: ConfigWidget[_FlatConfig] = ConfigWidget("test", _FlatConfig(), _FlatConfig, lambda _: None)
    async with _WidgetApp(widget).run_test() as pilot:
        pilot.app.query_one(Input).value = "Bob"
        await pilot.pause()
        result = widget.collect_config()
    assert result.name == "Bob"


async def test_config_widget_collect_config_after_checkbox_change() -> None:
    """Toggling a Checkbox is reflected when collect_config is called."""
    widget: ConfigWidget[_FlatConfig] = ConfigWidget("test", _FlatConfig(), _FlatConfig, lambda _: None)
    async with _WidgetApp(widget).run_test() as pilot:
        pilot.app.query_one(Checkbox).value = True
        await pilot.pause()
        result = widget.collect_config()
    assert result.active is True


async def test_config_widget_save_button_calls_callback() -> None:
    """Clicking Save calls the callback with the current configuration."""
    results: list[_FlatConfig] = []
    widget: ConfigWidget[_FlatConfig] = ConfigWidget("test", _FlatConfig(), _FlatConfig, results.append)
    async with _WidgetApp(widget).run_test() as pilot:
        await pilot.click("#save")
    assert len(results) == 1
    assert results[0] == _FlatConfig()


# --- ConfigScreen ---


async def test_config_screen_placeholder_visible_before_tabs() -> None:
    """Before any tabs are added, the placeholder is shown and the tabbed content is hidden."""
    async with _ScreenApp().run_test() as pilot:
        await pilot.pause()
        screen = cast("ConfigScreen", pilot.app.screen)
        assert screen.query_one(PlaceholderConfigWidget).display is True
        assert screen.query_one(TabbedContent).display is False


async def test_config_screen_new_tab_shows_tabbed_content() -> None:
    """Adding a tab hides the placeholder and reveals the tabbed content."""
    async with _ScreenApp().run_test() as pilot:
        await pilot.pause()
        screen = cast("ConfigScreen", pilot.app.screen)
        screen.new_tab("settings", _FlatConfig(), _FlatConfig, lambda _: None, title="Settings")
        await pilot.pause()
        assert screen.query_one(PlaceholderConfigWidget).display is False
        assert screen.query_one(TabbedContent).display is True


async def test_config_screen_duplicate_tab_name_raises() -> None:
    """Adding two tabs with the same name raises ValueError."""
    async with _ScreenApp().run_test() as pilot:
        await pilot.pause()
        screen = cast("ConfigScreen", pilot.app.screen)
        screen.new_tab("settings", _FlatConfig(), _FlatConfig, lambda _: None, title="Settings")
        with pytest.raises(ValueError, match="settings"):
            screen.new_tab("settings", _FlatConfig(), _FlatConfig, lambda _: None, title="Settings")
