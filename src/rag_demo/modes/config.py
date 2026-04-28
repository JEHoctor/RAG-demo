from __future__ import annotations

from enum import Enum
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    TabbedContent,
    TabPane,
)

from rag_demo.modes._logic_provider import LogicProviderScreen
from rag_demo.tree_mapping import TreeMapping

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from rich.console import RenderableType
    from textual.app import ComposeResult


def _sequential_ids(namespace: str) -> Iterator[str]:
    """Generate unique string ids for widgets of the form f"{namespace}.{sequence_number}".

    Args:
        namespace (str): a namespace for the ids

    Yields:
        str: a unique id
    """
    for sequence_number in count():
        yield f"generated-id.{namespace}.{sequence_number}"


class EnumRadioSet(RadioSet):
    """A radio button set built automatically from an enum."""

    def __init__(  # noqa: PLR0913
        self,
        default: Enum,
        *,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
        tooltip: RenderableType | None = None,
        compact: bool = False,
    ) -> None:
        """Initialize the radio set.

        Args:
            default: The default enum value.
            name: The name of the radio set.
            id: The ID of the radio set in the DOM.
            classes: The CSS classes of the radio set.
            disabled: Whether the radio set is disabled or not.
            tooltip: Optional tooltip.
            compact: Enable compact radio set style
        """
        self._default = default
        self._enum_type = type(default)
        self._options = list(self._enum_type)
        buttons = [RadioButton(option.name, value=option == default) for option in self._options]
        super().__init__(
            *buttons, name=name, id=id, classes=classes, disabled=disabled, tooltip=tooltip, compact=compact
        )

    def get_value(self) -> Enum:
        """Get the selected enum value."""
        if self.pressed_index < 0:
            raise ValueError
        return self._options[self.pressed_index]


class ConfigWidget[T: BaseModel](Widget):
    """Widget that updates dynamic configuration using a pydantic model."""

    def __init__(self, name: str, current_config: T, model: type[T], callback: Callable[[T], None]) -> None:
        """Initialize the config tab.

        Args:
            name (str): the name of the component being configured
            current_config (T: BaseModel): the current configuration
            model (type[T: BaseModel]): data model of the configuration options
            callback (Callable[[T: BaseModel], None]): the callback to call when the configuration changes
        """
        super().__init__()
        self._name: str = name
        self._config = current_config
        self._model = model
        self._callback = callback

        self._selections: TreeMapping[str, Any] = TreeMapping()
        self._id_to_field: dict[str, tuple[str, ...]] = {}
        self._id_generator = _sequential_ids(namespace=self._name)

    def compose(self) -> ComposeResult:
        """Compose the initial content of the widget."""
        with VerticalScroll(id="config-scroll"):
            yield from self._compose_helper(name=self._name, config=self._config, model=self._model)
        yield Button("Save Configuration", variant="primary", id="save")

    def _compose_helper(self, name: str, config: T, model: type[T], depth: tuple[str, ...] = ()) -> ComposeResult:
        yield Label(name)
        for field_name, field_info in model.model_fields.items():
            field_path: tuple[str, ...] = (*depth, field_name)
            if field_info.annotation is str:
                id_ = next(self._id_generator)
                self._id_to_field[id_] = field_path
                yield Input(getattr(config, field_name), id=id_)
            elif field_info.annotation is bool:
                id_ = next(self._id_generator)
                self._id_to_field[id_] = field_path
                yield Checkbox(label=field_name, value=getattr(config, field_name), id=id_)
            elif issubclass(field_info.annotation, BaseModel):
                yield from self._compose_helper(
                    name=field_name,
                    config=getattr(config, field_name),
                    model=field_info.annotation,
                    depth=field_path,
                )
            elif issubclass(field_info.annotation, Enum):
                id_ = next(self._id_generator)
                self._id_to_field[id_] = field_path
                yield EnumRadioSet(
                    default=getattr(config, field_name),
                    name=field_name,
                    id=id_,
                )
            else:
                raise NotImplementedError

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "save":
            config = self.collect_config()
            self._callback(config)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox change events."""
        self._selections[self._id_to_field[event.checkbox.id]] = event.value

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input change events."""
        self._selections[self._id_to_field[event.input.id]] = event.value

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio set change events."""
        self._selections[self._id_to_field[event.radio_set.id]] = cast("EnumRadioSet", event.control).get_value()

    def collect_config(self) -> T:
        """Create a configuration from the selected options."""
        base: dict[str, Any] = self._config.model_dump()
        for path, value in self._selections.items():
            target = base
            for segment in path[:-1]:
                target = target[segment]
            target[path[-1]] = value
        return self._model.model_validate(base)


class PlaceholderConfigWidget(Widget):
    """Placeholder content shown when configuration tabs have not yet been added to the config screen."""

    def compose(self) -> ComposeResult:
        """Compose the placeholder content."""
        with Container(id="placeholder-container"):
            yield Label(
                content="Configuration tabs will appear here when configurable\nparts of this application add them.",
                id="placeholder-text",
            )


class ConfigScreen(LogicProviderScreen):
    """Screen for configuring the application."""

    SUB_TITLE = "Configure"
    CSS_PATH = Path(__file__).parent / "config.tcss"

    def __init__(self) -> None:
        """Initialize the config screen."""
        super().__init__()
        # mapping from tab name to tab widget
        self._tabs: dict[str, ConfigWidget] = {}

    def compose(self) -> ComposeResult:
        """Compose the content of the config screen."""
        yield Header()
        yield PlaceholderConfigWidget(id="placeholder")
        yield TabbedContent(id="config-tabs")
        yield Footer()

    def on_mount(self) -> None:
        """Hide the tabbed content and display the placeholder until tabs are added."""
        self.query_one("#config-tabs", TabbedContent).display = False

    def new_tab[T: BaseModel](
        self,
        name: str,
        current_config: T,
        model: type[T],
        callback: Callable[[T], None],
        title: str,
    ) -> None:
        """Add configuration options for a named subsystem of the application.

        Args:
            name (str): name of the subsystem, must be unique within this ConfigScreen instance
            current_config (T: BaseModel): the current configuration
            model (type[T: BaseModel]): data model of the configuration options
            callback (Callable[[T: BaseModel], None]): the callback to call when the configuration changes
            title (str): title of the tab
        """
        if name in self._tabs:
            raise ValueError

        tab_widget = ConfigWidget[T](name=name, current_config=current_config, model=model, callback=callback)
        self._tabs[name] = tab_widget
        config_tabs = self.query_one("#config-tabs", TabbedContent)
        config_tabs.add_pane(TabPane(title, tab_widget))

        config_tabs.display = True
        self.query_one("#placeholder", PlaceholderConfigWidget).display = False
