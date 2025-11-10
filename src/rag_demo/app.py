from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Footer, Header, Input, Markdown


class RAGDemo(App):
    CSS = """
    ScrollableContainer {
        height: 100%;
        align: center middle;
    }
    Input {
        width: 80%;
        margin: 1;
    }
    """

    def __init__(self, username: str | None = None) -> None:
        super().__init__()
        self.username = username

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Ask a question...")
        yield ScrollableContainer(Markdown(id="response"))
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        # Todo: call LLM
        if self.username is not None:
            llm_response = f"{self.username} you asked: {event.value}"
        else:
            llm_response = f"You asked: {event.value}"

        markdown_widget = self.query_one("#response", Markdown)
        await markdown_widget.update(llm_response)
