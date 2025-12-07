from datasets import DatasetDict, load_dataset
from huggingface_hub import hf_hub_download
from langchain_community.chat_models import ChatLlamaCpp
from langchain_ollama import ChatOllama

from rag_demo.dirs import CONFIG_DIR, DATA_DIR


def get_chat_ollama() -> ChatOllama:
    return ChatOllama(
        model="gemma3:latest",
        validate_model_on_init=True,
        temperature=0.5,
        num_predict=4096,
    )


def get_chat_llama_cpp() -> ChatLlamaCpp:
    model_path = hf_hub_download(
        repo_id="unsloth/Qwen3-4B-Instruct-2507-GGUF",
        filename="Qwen3-4B-Instruct-2507-F16.gguf",  # 8.05GB
        revision="a06e946bb6b655725eafa393f4a9745d460374c9",
    )

    return ChatLlamaCpp(
        model_path=model_path,
        n_ctx=32_768,
        n_batch=64,
        max_tokens=32_768,
        temperature=0.7,
        top_k=20,
        top_p=0.80,
        verbose=False,
    )


llm = get_chat_llama_cpp()


def get_wikipedia_dataset():
    return load_dataset("wikipedia", "20220301.en")


def get_rag_mini_wikipedia() -> tuple[DatasetDict, DatasetDict]:
    mini_wiki_qa: DatasetDict = load_dataset("rag-datasets/rag-mini-wikipedia", "question-answer")  # type: ignore
    mini_wiki_corpus: DatasetDict = load_dataset("rag-datasets/rag-mini-wikipedia", "text-corpus")  # type: ignore
    return mini_wiki_qa, mini_wiki_corpus


starter_messages = [
    ("system", "You are a helpful assistant."),
]

messages = starter_messages.copy()


def reset():
    global messages
    messages = starter_messages.copy()


class Conversation:
    def __init__(self):
        self.messages = messages.copy()
