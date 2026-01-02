from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Static,
)

from rag_demo.modes._logic_provider import LogicProviderScreen


class ConfigScreen(LogicProviderScreen):
    SUB_TITLE = "Configure"
    CSS_PATH = Path(__file__).parent / "config.tcss"

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
            Input(placeholder="sk-...", password=True, id="api-key"),
            Label("Base URL (for Ollama):"),
            Input(placeholder="http://localhost:11434", id="base-url"),
            Label("Model Path (for LlamaCpp):"),
            Input(placeholder="/path/to/model.gguf", id="model-path"),
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
        api_key = self.query_one("#api-key", Input).value
        base_url = self.query_one("#base-url", Input).value
        model_path = self.query_one("#model-path", Input).value

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
