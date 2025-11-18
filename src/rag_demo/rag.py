from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="gemma3:latest",
    validate_model_on_init=True,
    temperature=0.5,
    num_predict=4096,
)

messages = [
    ("system", "You are a helpful assistant."),
]
