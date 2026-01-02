from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Input

if TYPE_CHECKING:
    from collections.abc import Iterable

    from rich.console import RenderableType
    from rich.highlighter import Highlighter
    from textual.events import Key
    from textual.suggester import Suggester
    from textual.validation import Validator
    from textual.widget import Widget
    from textual.widgets._input import InputType, InputValidationOn


class EscapableInput(Input):
    """An input widget that deselects itself when the user presses escape.

    Inherits all properties and methods from the :class:`textual.widgets.Input` class.
    """

    def __init__(  # noqa: PLR0913
        self,
        value: str | None = None,
        placeholder: str = "",
        highlighter: Highlighter | None = None,
        password: bool = False,  # noqa: FBT001, FBT002
        *,
        restrict: str | None = None,
        type: InputType = "text",  # noqa: A002
        max_length: int = 0,
        suggester: Suggester | None = None,
        validators: Validator | Iterable[Validator] | None = None,
        validate_on: Iterable[InputValidationOn] | None = None,
        valid_empty: bool = False,
        select_on_focus: bool = True,
        name: str | None = None,
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
        tooltip: RenderableType | None = None,
        compact: bool = False,
        focus_on_escape: Widget | None = None,
    ) -> None:
        """Initialise the `EscapableInput` widget.

        Args:
            value: An optional default value for the input.
            placeholder: Optional placeholder text for the input.
            highlighter: An optional highlighter for the input.
            password: Flag to say if the field should obfuscate its content.
            restrict: A regex to restrict character inputs.
            type: The type of the input.
            max_length: The maximum length of the input, or 0 for no maximum length.
            suggester: [`Suggester`][textual.suggester.Suggester] associated with this
                input instance.
            validators: An iterable of validators that the Input value will be checked against.
            validate_on: Zero or more of the values "blur", "changed", and "submitted",
                which determine when to do input validation. The default is to do
                validation for all messages.
            valid_empty: Empty values are valid.
            select_on_focus: Whether to select all text on focus.
            name: Optional name for the input widget.
            id: Optional ID for the widget.
            classes: Optional initial classes for the widget.
            disabled: Whether the input is disabled or not.
            tooltip: Optional tooltip.
            compact: Enable compact style (without borders).
            focus_on_escape: An optional widget to focus on when escape is pressed. Defaults to `None`.
        """
        super().__init__(
            value=value,
            placeholder=placeholder,
            highlighter=highlighter,
            password=password,
            restrict=restrict,
            type=type,
            max_length=max_length,
            suggester=suggester,
            validators=validators,
            validate_on=validate_on,
            valid_empty=valid_empty,
            select_on_focus=select_on_focus,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            tooltip=tooltip,
            compact=compact,
        )
        self.focus_on_escape = focus_on_escape

    def on_key(self, event: Key) -> None:
        """Deselect the input if the event is the escape key.

        This method overrides the base :meth:`textual.widgets.Input.on_key` implementation.

        Args:
            event (Key): Event details, including the key pressed.
        """
        if event.key == "escape":
            if self.focus_on_escape is not None:
                self.focus_on_escape.focus()
            else:
                self.blur()
            event.prevent_default()
            event.stop()
