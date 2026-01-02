import time
from pathlib import Path
from typing import TYPE_CHECKING

import pyperclip
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Static

from rag_demo import rag
from rag_demo.markdown import parser_factory
from rag_demo.modes._logic_provider import LogicProviderScreen, LogicProviderWidget
from rag_demo.widgets import EscapableInput

if TYPE_CHECKING:
    from textual.widgets.markdown import MarkdownStream


class Response(LogicProviderWidget):
    """Allow toggling between raw and rendered versions of markdown text."""

    show_raw = reactive(False, layout=True)
    content = reactive("", layout=True)

    def __init__(self, *, content: str = "", classes: str | None = None) -> None:
        super().__init__(classes=classes)
        self.set_reactive(Response.content, content)
        self.stop_requested = False

    def compose(self) -> ComposeResult:
        with VerticalGroup():
            with HorizontalGroup(id="header"):
                yield Label("Chunks/s: ???", id="token-rate")
                with HorizontalGroup(id="buttons"):
                    yield Button("Stop", id="stop", variant="primary")
                    yield Button("Show Raw", id="show-raw", variant="primary")
                    yield Button("Copy", id="copy", variant="primary")
            yield Markdown(self.content, id="markdown-view", parser_factory=parser_factory)
            yield Static(self.content, id="raw-view")

    def on_mount(self) -> None:
        self.query_one("#raw-view", Static).display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "stop":
            self.stop_requested = True
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
        button = self.query_one("#show-raw", Button)
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
        rate_widget = self.query_one("#token-rate", Label)
        stop_button = self.query_one("#stop", Button)
        stream: MarkdownStream | None = None
        n_chunks = 0
        start = time.time()
        try:
            first = True
            async for chunk in self.logic.llm.astream(rag.messages):
                if not isinstance(chunk.content, str):
                    self.app.log.error(f"Received non-string response from LLM of type {type(chunk.content)}")
                    continue
                n_chunks += 1
                rate = n_chunks / (time.time() - start)
                rate_widget.update(f"Chunks/s: {rate:.2f}")
                if first:
                    response = chunk.content
                    self.set_reactive(Response.content, response)
                    md_widget.update(response)
                    raw_widget.update(response)
                    stream = Markdown.get_stream(md_widget)
                    first = False
                else:
                    response += chunk.content
                    self.set_reactive(Response.content, response)
                    # Ignore type checker below: stream cannot be None at this point.
                    await stream.write(chunk.content)  # type: ignore
                    raw_widget.update(response)
                if self.stop_requested:
                    self.stop_requested = False
                    break
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
        finally:
            stop_button.display = False


class ChatScreen(LogicProviderScreen):
    SUB_TITLE = "Chat"
    CSS_PATH = Path(__file__).parent / "chat.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.generating = False

    def compose(self) -> ComposeResult:
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
        self.query_one("#new-request", Input).focus()
        self.query_one("#chats", VerticalScroll).anchor()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-conversation":
            self.app.notify(f"Dear {self.logic.username}, 'New Conversation' is not implemented yet", severity="error")
            chats = self.query_one("#chats", VerticalScroll)
            for child in chats.children:
                if child.id == "top-chat-separator":
                    continue
                if isinstance(child, Response):
                    child.stop_requested = True
                child.remove()
            rag.reset()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "new-request":
            if self.generating:
                return
            new_request = event.value
            if not new_request:
                return
            self.generating = True

            self.query_one("#new-request", Input).value = ""
            rag.messages.append(("human", new_request))

            conversation = self.query_one("#chats", VerticalScroll)
            new_response_md = Response(content="Waiting for AI to respond...", classes="response")

            conversation.mount(HorizontalGroup(Label(new_request, classes="request"), classes="request-container"))
            conversation.mount(HorizontalGroup(new_response_md, classes="response-container"))
            conversation.anchor()

            self.run_worker(self.stream_response(new_response_md))

    async def stream_response(self, response_md: Response) -> None:
        await response_md.stream_response()
        self.generating = False
