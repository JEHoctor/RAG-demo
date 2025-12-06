import time
from pathlib import Path
from typing import TYPE_CHECKING

import pyperclip
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.events import Key
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Static

from rag_demo import rag
from rag_demo.markdown import parser_factory
from rag_demo.modes._rag_demo_screen import RAGDemoScreen

if TYPE_CHECKING:
    from textual.widgets.markdown import MarkdownStream


class EscapableInput(Input):
    """An input widget that deselects itself when the user presses escape.

    Inherits all properties and methods from the :class:`textual.widgets.Input` class.
    """

    def on_key(self, event: Key) -> None:
        """Deselect the input if the event is the escape key.

        This method overrides the base :meth:`textual.widgets.Input.on_key` implementation.

        Args:
            event (Key): Event details, including the key pressed.
        """
        if event.key == "escape":
            self.blur()
            event.prevent_default()
            event.stop()


class Response(Widget):
    """Allow toggling between raw and rendered versions of markdown text."""

    show_raw = reactive(False, layout=True)
    content = reactive("", layout=True)

    def __init__(self, *, content: str = "", classes: str | None = None) -> None:
        super().__init__(classes=classes)
        self.set_reactive(Response.content, content)

    def compose(self) -> ComposeResult:
        with VerticalGroup():
            with HorizontalGroup(id="buttons"):
                yield Button("Show Raw", id="show_raw", variant="primary")
                yield Button("Copy", id="copy", variant="primary")
            yield Markdown(self.content, id="markdown-view", parser_factory=parser_factory)
            yield Static(self.content, id="raw-view")

    def on_mount(self) -> None:
        self.query_one("#raw-view", Static).display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show_raw":
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
            except Exception as e:
                self.app.log.error(f"Error copying to clipboard with Pyperclip: {e}")
            checkpoint2 = time.time()
            self.notify(f"Copied {len(self.content.splitlines())} lines of text to clipboard")
            end = time.time()
            self.app.log.info(f"Textual copy took {checkpoint - start:.6f} seconds")
            self.app.log.info(f"Pyperclip copy took {checkpoint2 - checkpoint:.6f} seconds")
            self.app.log.info(f"Notify took {end - checkpoint2:.6f} seconds")
            self.app.log.info(f"Total of {end - start:.6f} seconds")

    def watch_show_raw(self) -> None:
        button = self.query_one("#show_raw", Button)
        markdown_view = self.query_one("#markdown-view", Markdown)
        raw_view = self.query_one("#raw-view", Static)

        if self.show_raw:
            button.label = "Show Rendered"
            markdown_view.display = False
            raw_view.display = True
        else:
            button.label = "Show Raw"
            markdown_view.display = True
            raw_view.display = False

    def watch_content(self, content: str) -> None:
        self.query_one("#markdown-view", Markdown).update(content)
        self.query_one("#raw-view", Static).update(content)

    async def stream_response(self) -> None:
        response: str = ""
        md_widget = self.query_one("#markdown-view", Markdown)
        raw_widget = self.query_one("#raw-view", Static)
        stream: MarkdownStream | None = None
        try:
            first = True
            async for chunk in rag.llm.astream(rag.messages):
                if not isinstance(chunk.content, str):
                    self.app.log.error(f"Received non-string response from LLM of type {type(chunk.content)}")
                    continue
                if first:
                    response = chunk.content
                    self.set_reactive(Response.content, response)
                    md_widget.update(response)
                    raw_widget.update(response)
                    stream = Markdown.get_stream(md_widget)
                    first = False
                    continue
                response += chunk.content
                self.set_reactive(Response.content, response)
                # Ignore type checker below: stream cannot be None at this point.
                await stream.write(chunk.content)  # type: ignore
                raw_widget.update(response)
        except Exception as e:
            if stream is not None:
                await stream.stop()
            content = f"Error: {e}"
            self.set_reactive(Response.content, content)
            md_widget.update(content)
            raw_widget.update(content)
        else:
            if stream is not None:
                await stream.stop()
            rag.messages.append(("ai", response))
            md_widget.update(response)


class ChatScreen(RAGDemoScreen):
    SUB_TITLE = "Chat"
    CSS_PATH = Path(__file__).parent / "chat.tcss"

    def __init__(self, username: str | None = None) -> None:
        super().__init__()
        self.username = username
        self.generating = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="chats"):
            yield HorizontalGroup(id="top_chat_separator")
        with HorizontalGroup(id="new_request_bar"):
            yield Static()
            yield Button("New Conversation", id="new_conversation")
            yield EscapableInput(placeholder="     What do you want to know?", id="new_request")
            yield Static()
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#new_request", Input).focus()
        self.query_one("#chats", VerticalScroll).anchor()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new_conversation":
            self.app.notify(f"Dear {self.logic.username}, 'New Conversation' is not implemented yet", severity="error")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "new_request":
            if self.generating:
                return
            new_request = event.value
            if not new_request:
                return
            self.generating = True

            self.query_one("#new_request", Input).value = ""
            rag.messages.append(("human", new_request))

            conversation = self.query_one("#chats", VerticalScroll)
            new_response_md = Response(content="Waiting for AI to respond...", classes="response")

            conversation.mount(HorizontalGroup(Label(new_request, classes="request"), classes="request_container"))
            conversation.mount(HorizontalGroup(new_response_md, classes="response_container"))
            conversation.anchor()

            self.run_worker(self.stream_response(new_response_md))

    async def stream_response(self, response_md: Response) -> None:
        await response_md.stream_response()
        self.generating = False
