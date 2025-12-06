import time
from pathlib import Path

import pyperclip
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, HorizontalGroup, VerticalGroup, VerticalScroll
from textual.events import Key
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    RadioButton,
    RadioSet,
    Static,
)
from textual.widgets.markdown import MarkdownStream

from rag_demo import rag
from rag_demo.markdown import parser_factory


class ConfigScreen(Screen):
    SUB_TITLE = "Configure"
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("🤖 LLM Configuration", classes="title"),
            Label("Select your LLM provider:"),
            RadioSet(
                RadioButton("OpenAI (API)", id="openai"),
                RadioButton("Anthropic Claude (API)", id="anthropic"),
                RadioButton("Ollama (Local)", id="ollama"),
                RadioButton("LlamaCpp (Local)", id="llamacpp"),
                id="provider",
            ),
            Label("Model name:"),
            Input(placeholder="e.g., gpt-4, claude-3-sonnet-20240229", id="model"),
            Label("API Key (if applicable):"),
            Input(placeholder="sk-...", password=True, id="api_key"),
            Label("Base URL (for Ollama):"),
            Input(placeholder="http://localhost:11434", id="base_url"),
            Label("Model Path (for LlamaCpp):"),
            Input(placeholder="/path/to/model.gguf", id="model_path"),
            Horizontal(
                Button("Save & Continue", variant="primary", id="save"),
                Button("Cancel", id="cancel"),
            ),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            config = self.collect_config()
            self.app.config_manager.save_config(config)
            self.app.pop_screen()  # Return to main app
        elif event.button.id == "cancel":
            self.app.exit()

    def collect_config(self) -> dict:
        provider = self.query_one("#provider", RadioSet).pressed_button.id
        model = self.query_one("#model", Input).value
        api_key = self.query_one("#api_key", Input).value
        base_url = self.query_one("#base_url", Input).value
        model_path = self.query_one("#model_path", Input).value

        config = {
            "provider": provider,
            "model": model,
        }

        if api_key:
            config["api_key"] = api_key
        if base_url:
            config["base_url"] = base_url
        if model_path:
            config["model_path"] = model_path

        return config


class EscapableInput(Input):
    def on_key(self, event: Key) -> None:
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


class RAGScreen(Screen):
    SUB_TITLE = "Chat"

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
            self.app.notify("New conversation not implemented yet", severity="error")

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


class RAGDemo(App):
    TITLE = "RAG Demo"
    CSS_PATH = Path(__file__).parent / "rag_demo.tcss"
    BINDINGS = [
        Binding("z", "app.push_screen('chat')", "Chat"),
        Binding("c", "app.push_screen('config')", "Configure"),
    ]

    def __init__(self, username: str | None = None) -> None:
        super().__init__()
        self.username = username

    def on_mount(self) -> None:
        self.install_screen(RAGScreen(username=self.username), name="chat")
        self.install_screen(ConfigScreen(), name="config")
        self.push_screen("chat")
