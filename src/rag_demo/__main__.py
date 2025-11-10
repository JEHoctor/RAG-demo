import typer


def _main(name: str | None = None) -> None:
    if name is not None:
        print(f"Hello {name} from rag-demo!")
    else:
        print("Hello from rag-demo!")


def main():
    typer.run(_main)


if __name__ == "__main__":
    main()
