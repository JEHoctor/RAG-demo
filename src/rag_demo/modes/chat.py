from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyperclip
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Pretty, Static
from textual.widgets.markdown import MarkdownStream

from rag_demo.markdown import parser_factory
from rag_demo.modes._logic_provider import LogicProviderScreen, LogicProviderWidget
from rag_demo.widgets import EscapableInput

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from textual.app import ComposeResult


class ResponseStreamInProgressError(ValueError):
    """Exception raised when a Response widget already has an open writer stream."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__("This Response widget already has an open writer stream.")


class StoppedStreamError(ValueError):
    """Exception raised when a ResponseWriter is asked to write after it has been stopped."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__("Can't write to a stopped ResponseWriter stream.")


class ResponseWriter:
    """Stream markdown to a Response widget as if it were a simple Markdown widget.

    This handles streaming to the Markdown widget and updating the raw text widget and the generation rate label.

    This class is based on the MarkdownStream class from the Textual library.
    """

    def __init__(self, response_widget: Response) -> None:
        """Initialize a new ResponseWriter.

        Args:
            response_widget (Response): The Response widget to write to.
        """
        self.response_widget = response_widget
        self._markdown_widget = response_widget.query_one("#markdown-view", Markdown)
        self._markdown_stream = MarkdownStream(self._markdown_widget)
        self._raw_widget = response_widget.query_one("#raw-view", Label)
        self._start_time: float | None = None
        self._n_chunks = 0
        self._response_text = ""
        self._stopped = False

    async def stop(self) -> None:
        """Stop this ResponseWriter, particularly its underlying MarkdownStream."""
        self._stopped = True
        # This is safe even if the MarkdownStream has not been started, or has already been stopped.
        await self._markdown_stream.stop()
        # Because of the markdown parsing tweaks I made in src/rag_demo/markdown.py, we need to reparse the final
        # markdown and rerender one more time to clean up small issues with newlines.
        self._markdown_widget.update(self._response_text)

    async def write(self, markdown_fragment: str) -> None:
        """Stream a single chunk/fragment to the corresponding Response widget.

        Args:
            markdown_fragment (str): The new markdown fragment to append to the existing markdown.

        Raises:
            StoppedStreamError: Raised if the new markdown chunk cannot be accepted because the stream has been stopped.
        """
        if self._stopped:
            raise StoppedStreamError
        write_time = time.time()
        self._response_text += markdown_fragment
        self.response_widget.set_reactive(Response.content, self._response_text)
        self._raw_widget.update(self._response_text)
        if self._start_time is None:
            # The first chunk. Can't set the rate label until we have a second chunk.
            self._start_time = write_time

            self._markdown_widget.update(markdown_fragment)
            self._markdown_stream.start()
        else:
            # The second and subsequent chunks. Note that self._n_chunks has not been incremented yet because
            # we are calculating the generation rate excluding the first chunk, which may have required loading a
            # large model.
            rate = self._n_chunks / (write_time - self._start_time)
            self.response_widget.update_rate_label(rate)

            await self._markdown_stream.write(markdown_fragment)
        self._n_chunks += 1


class Response(LogicProviderWidget):
    """Allow toggling between raw and rendered versions of markdown text."""

    show_raw = reactive(False, layout=True)
    content = reactive("", layout=True)

    def __init__(self, *, content: str = "", classes: str | None = None) -> None:
        """Initialize a new Response widget.

        Args:
            content (str, optional): Initial response text. Defaults to empty string.
            classes (str | None, optional): Optional widget classes for use with TCSS. Defaults to None.
        """
        super().__init__(classes=classes)
        self.set_reactive(Response.content, content)
        self._stream: ResponseWriter | None = None
        self.__object_to_show_sentinel = object()
        self._object_to_show: Any = self.__object_to_show_sentinel

    def compose(self) -> ComposeResult:
        """Compose the initial content of the widget."""
        with VerticalGroup():
            with HorizontalGroup(id="header"):
                yield Label("Chunks/s: ???", id="token-rate")
                with HorizontalGroup(id="buttons"):
                    yield Button("Stop", id="stop", variant="primary")
                    yield Button("Show Raw", id="show-raw", variant="primary")
                    yield Button("Copy", id="copy", variant="primary")
            yield Markdown(self.content, id="markdown-view", parser_factory=parser_factory)
            yield Label(self.content, id="raw-view", markup=False)
            yield Pretty(None, id="object-view")

    def on_mount(self) -> None:
        """Hide certain elements until they are needed."""
        self.query_one("#raw-view", Label).display = False
        self.query_one("#object-view", Pretty).display = False
        self.query_one("#stop", Button).display = False

    def set_shown_object(self, obj: Any) -> None:  # noqa: ANN401
        self._object_to_show = obj
        self.query_one("#markdown-view", Markdown).display = False
        self.query_one("#raw-view", Label).display = False
        self.query_one("#show-raw", Button).display = False
        self.query_one("#object-view", Pretty).update(obj)
        self.query_one("#object-view", Pretty).display = True

    def clear_shown_object(self) -> None:
        self._object_to_show = self.__object_to_show_sentinel
        if self.show_raw:
            self.query_one("#show-raw", Button).display = True
        else:
            self.query_one("#markdown-view", Markdown).display = True

    @asynccontextmanager
    async def stream_writer(self) -> AsyncIterator[ResponseWriter]:
        """Open an exclusive stream to write markdown in chunks.

        Raises:
            ResponseWriteInProgressError: Raised when there is already an open stream.

        Yields:
            ResponseWriter: _description_
        """
        if self._stream is not None:
            raise ResponseStreamInProgressError
        self._stream = ResponseWriter(self)
        self.query_one("#stop", Button).display = True
        try:
            yield self._stream
        finally:
            await self._stream.stop()
            self.query_one("#stop", Button).display = False
            self._stream = None

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "stop":
            if self._stream is not None:
                await self._stream.stop()
        elif event.button.id == "show-raw":
            self.show_raw = not self.show_raw
        elif event.button.id == "copy":
            # Textual and Pyperclip use different methods to copy text to the clipboard. Textual uses ANSI escape
            # sequence magic that is not supported by all terminals. Pyperclip uses OS-specific clipboard APIs, but it
            # does not work over SSH.
            start = time.time()
            self.app.copy_to_clipboard(self.content)
            checkpoint = time.time()
            try:
                pyperclip.copy(self.content)
            except pyperclip.PyperclipException as e:
                self.app.log.error(f"Error copying to clipboard with Pyperclip: {e}")
            checkpoint2 = time.time()
            self.notify(f"Copied {len(self.content.splitlines())} lines of text to clipboard")
            end = time.time()
            self.app.log.info(f"Textual copy took {checkpoint - start:.6f} seconds")
            self.app.log.info(f"Pyperclip copy took {checkpoint2 - checkpoint:.6f} seconds")
            self.app.log.info(f"Notify took {end - checkpoint2:.6f} seconds")
            self.app.log.info(f"Total of {end - start:.6f} seconds")

    def watch_show_raw(self) -> None:
        """Handle reactive updates to the show_raw attribute by changing the visibility of the child widgets.

        This also keeps the text on the visibility toggle button up-to-date.
        """
        if self._object_to_show is not self.__object_to_show_sentinel:
            return
        button = self.query_one("#show-raw", Button)
        markdown_view = self.query_one("#markdown-view", Markdown)
        raw_view = self.query_one("#raw-view", Label)

        if self.show_raw:
            button.label = "Show Rendered"
            markdown_view.display = False
            raw_view.display = True
        else:
            button.label = "Show Raw"
            markdown_view.display = True
            raw_view.display = False

    def watch_content(self, content: str) -> None:
        """Handle reactive updates to the content attribute by updating the markdown and raw views.

        Args:
            content (str): New content for the widget.
        """
        self.query_one("#markdown-view", Markdown).update(content)
        self.query_one("#raw-view", Label).update(content)

    def update_rate_label(self, rate: float | None) -> None:
        """Update or reset the generation rate indicator.

        Args:
            rate (float | None): Generation rate, or None to reset. Defaults to None.
        """
        label_text = "Chunks/s: ???" if rate is None else f"Chunks/s: {rate:.2f}"
        self.query_one("#token-rate", Label).update(label_text)


class ChatScreen(LogicProviderScreen):
    """Main mode of the app. Talk to the AI agent."""

    SUB_TITLE = "Chat"
    CSS_PATH = Path(__file__).parent / "chat.tcss"

    def compose(self) -> ComposeResult:
        """Compose the initial content of the chat screen."""
        yield Header()
        chats = VerticalScroll(id="chats")
        with chats:
            yield HorizontalGroup(id="top-chat-separator")
        with HorizontalGroup(id="new-request-bar"):
            yield Static()
            yield Button("New Conversation", id="new-conversation")
            yield EscapableInput(placeholder="     What do you want to know?", id="new-request", focus_on_escape=chats)
            yield Static()
        yield Footer()

    def on_mount(self) -> None:
        """When the screen is mounted, focus the input field and enable bottom anchoring for the message view."""
        self.query_one("#new-request", Input).focus()
        self.query_one("#chats", VerticalScroll).anchor()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "new-conversation":
            self.logic.new_conversation(self)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle submission of new requests."""
        if event.input.id == "new-request":
            accepted = await self.logic.submit_request(self, event.value)
            if accepted:
                self.query_one("#new-request", Input).value = ""

    def clear_chats(self) -> None:
        """Clear the chat scroll area."""
        chats = self.query_one("#chats", VerticalScroll)
        for child in chats.children:
            if child.id != "top-chat-separator":
                child.remove()

    def new_request(self, request_text: str) -> Label:
        """Create a new request element in the chat area.

        Args:
            request_text (str): The text of the request.

        Returns:
            Label: The request element.
        """
        chats = self.query_one("#chats", VerticalScroll)
        request = Label(request_text, classes="request")
        chats.mount(HorizontalGroup(request, classes="request-container"))
        chats.anchor()
        return request

    def new_response(self, response_text: str = "Waiting for AI to respond...") -> Response:
        """Create a new response element in the chat area.

        Args:
            response_text (str, optional): Initial response text. Usually this is a default message shown before
                streaming the actual response. Defaults to "Waiting for AI to respond...".

        Returns:
            Response: The response widget/element.
        """
        chats = self.query_one("#chats", VerticalScroll)
        response = Response(content=response_text, classes="response")
        chats.mount(HorizontalGroup(response, classes="response-container"))
        chats.anchor()
        return response
