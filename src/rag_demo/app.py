from pathlib import Path

from markdown_it import MarkdownIt
from textual import log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.events import Callback, Key
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
    Select,
    Static,
)

from rag_demo import rag


class ConfigScreen(Screen):
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
        with Vertical():
            yield Button("Show Raw", id="show_raw", classes="toggle-button")
            yield Markdown(
                self.content,
                id="markdown-view",
                parser_factory=lambda: MarkdownIt("gfm-like", {"breaks": True}),
            )
            yield Static(self.content, id="raw-view")

    def on_mount(self) -> None:
        self.query_one("#raw-view", Static).display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show_raw":
            self.show_raw = not self.show_raw

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


class RAGScreen(Screen):
    def __init__(self, username: str | None = None) -> None:
        super().__init__()
        self.username = username
        self.generating = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(id="chats")
        yield EscapableInput(placeholder="     What do you want to know?", id="new_request")
        yield Footer()

    def on_mount(self) -> None:
        request_input = self.query_one("#new_request", Input)
        request_input.focus()
        request_input.BINDINGS.append(Binding("escape", "blur", "Deselect Input"))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "new_request":
            if self.generating:
                return
            self.generating = True

            new_request = event.value
            if not new_request:
                return
            self.query_one("#new_request", Input).value = ""
            rag.messages.append(("human", new_request))

            conversation = self.query_one("#chats", ScrollableContainer)
            new_response_md = Response(content="Waiting for AI to respond...", classes="response")

            tracking_bottom = conversation.scroll_y >= conversation.max_scroll_y - 1
            conversation.mount(Label(new_request, classes="request"))
            conversation.mount(new_response_md)
            if tracking_bottom:
                conversation.scroll_end(animate=False)

            self.run_worker(self.stream_response(new_request, new_response_md, conversation), exclusive=True)

    async def stream_response(
        self, new_request: str, new_response_md: Response, conversation: ScrollableContainer
    ) -> None:
        response = ""
        try:
            async for chunk in rag.llm.astream(rag.messages):
                if chunk.content is None:
                    continue
                response += chunk.content

                tracking_bottom = conversation.scroll_y >= conversation.max_scroll_y - 1
                new_response_md.content = response
                if tracking_bottom:
                    conversation.scroll_end(animate=False)
        except Exception as e:
            new_response_md.content = f"Error: {e}"
        finally:
            rag.messages.append(("ai", response))
            self.query_one("#new_request", Input).disabled = False
            self.generating = False


class RAGDemo(App):
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
