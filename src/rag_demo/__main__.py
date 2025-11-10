import typer

from rag_demo.app import RAGDemo


def _main(name: str | None = None) -> None:
    app = RAGDemo(username=name)
    app.run()


def main():
    typer.run(_main)


if __name__ == "__main__":
    main()
