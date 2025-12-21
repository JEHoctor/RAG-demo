import contextlib
import platform
import sqlite3
from pathlib import Path
from typing import cast

import cpuinfo
import httpx
import huggingface_hub
import llama_cpp
import ollama
import psutil
import pynvml
from datasets import Dataset, load_dataset
from huggingface_hub import hf_hub_download
from huggingface_hub.constants import HF_HUB_CACHE
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_community.chat_models import ChatLlamaCpp
from langchain_community.embeddings import LlamaCppEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver

from rag_demo import dirs


class Logic:
    """Top-level application logic."""

    def __init__(self, username: str | None = None) -> None:
        """Initialize the application logic.

        Args:
            username (str | None, optional): The username provided as a command line argument. Defaults to None.
        """
        self.username = username
        if self.probe_ollama() is not None:
            ollama.pull("gemma3:latest")  # 3.3GB
            ollama.pull("embeddinggemma:latest")  # 621MB
            self.llm = ChatOllama(
                model="gemma3:latest",
                validate_model_on_init=True,
                temperature=0.5,
                num_predict=4096,
            )
            self.embed = OllamaEmbeddings(model="embeddinggemma:latest")
        else:
            model_path = hf_hub_download(
                repo_id="bartowski/google_gemma-3-4b-it-GGUF",
                filename="google_gemma-3-4b-it-Q6_K_L.gguf",  # 3.35GB
                revision="71506238f970075ca85125cd749c28b1b0eee84e",
            )
            embedding_model_path = hf_hub_download(
                repo_id="CompendiumLabs/bge-small-en-v1.5-gguf",
                filename="bge-small-en-v1.5-q8_0.gguf",  # 36.8MB
                revision="d32f8c040ea3b516330eeb75b72bcc2d3a780ab7",
            )
            self.llm = ChatLlamaCpp(model_path=model_path, verbose=False)
            self.embed = LlamaCppEmbeddings(model_path=embedding_model_path, verbose=False)  # pyright: ignore[reportCallIssue]

        self._conn = sqlite3.connect(database=dirs.DATA_DIR / "checkpoints.sqlite3", check_same_thread=False)
        self.agent = create_agent(
            model=self.llm,
            system_prompt="You are a helpful assistant.",
            checkpointer=SqliteSaver(self._conn),
        )
        self.current_thread = 1

        # RAG:
        self.qa_test: Dataset = cast(
            "Dataset",
            load_dataset("rag-datasets/rag-mini-wikipedia", "question-answer", split="test"),
        )
        self.corpus: Dataset = cast(
            "Dataset",
            load_dataset("rag-datasets/rag-mini-wikipedia", "text-corpus", split="passages"),
        )

    def invoke_current_agent(self, message: str) -> dict:
        """Send a message to the current agent and thread, returning the response."""
        return self.agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            {"configurable": {"thread_id": str(self.current_thread)}},
        )

    def probe_os(self) -> str:
        """Returns the OS name (eg 'Linux' or 'Windows'), the system name (eg 'Java'), or an empty string if unknown."""
        return platform.system()

    def probe_architecture(self) -> str:
        """Returns the machine architecture, such as 'i386'."""
        return platform.machine()

    def probe_cpu(self) -> str:
        """Returns the name of the CPU, e.g. "Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz"."""
        return cpuinfo.get_cpu_info()["brand_raw"]

    def probe_ram(self) -> int:
        """Returns the total amount of RAM in bytes."""
        return psutil.virtual_memory().total

    def probe_disk_space(self) -> int:
        """Returns the amount of free space in the root directory (in bytes)."""
        return psutil.disk_usage("/").free

    def probe_llamacpp_gpu_support(self) -> bool:
        """Returns True if LlamaCpp supports GPU offloading, False otherwise."""
        return llama_cpp.llama_supports_gpu_offload()

    def probe_huggingface_free_cache_space(self) -> int | None:
        """Returns the amount of free space in the Hugging Face cache (in bytes), or None if it can't be determined."""
        with contextlib.suppress(FileNotFoundError):
            return psutil.disk_usage(HF_HUB_CACHE).free
        for parent_dir in Path(HF_HUB_CACHE).parents:
            with contextlib.suppress(FileNotFoundError):
                return psutil.disk_usage(str(parent_dir)).free
        return None

    def probe_huggingface_cached_models(self) -> list[huggingface_hub.CachedRepoInfo] | None:
        """Returns a list of models in the Hugging Face cache (possibly empty), or None if the cache doesn't exist."""
        # The docstring for huggingface_hub.scan_cache_dir says it raises CacheNotFound "if the cache directory does not
        # exist," and ValueError "if the cache directory is a file, instead of a directory."
        with contextlib.suppress(ValueError, huggingface_hub.CacheNotFound):
            return [repo for repo in huggingface_hub.scan_cache_dir().repos if repo.repo_type == "model"]
        return None  # Isn't it nice to be explicit?

    def probe_huggingface_cached_datasets(self) -> list[huggingface_hub.CachedRepoInfo] | None:
        """Returns a list of datasets in the Hugging Face cache (possibly empty), or None if the cache doesn't exist."""
        with contextlib.suppress(ValueError, huggingface_hub.CacheNotFound):
            return [repo for repo in huggingface_hub.scan_cache_dir().repos if repo.repo_type == "dataset"]
        return None

    def probe_nvidia(self) -> tuple[int, list[str]]:
        """Detect available NVIDIA GPUs and CUDA driver version.

        Returns:
            tuple[int, list[str]]: A tuple (cuda_version, nv_gpus) where cuda_version is the installed CUDA driver
                version and nv_gpus is a list of GPU models corresponding to installed NVIDIA GPUs
        """
        try:
            pynvml.nvmlInit()
        except pynvml.NVMLError:
            return -1, []
        cuda_version = -1
        nv_gpus = []
        try:
            cuda_version = pynvml.nvmlSystemGetCudaDriverVersion()
            for i in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                nv_gpus.append(pynvml.nvmlDeviceGetName(handle))
        except pynvml.NVMLError:
            pass
        finally:
            with contextlib.suppress(pynvml.NVMLError):
                pynvml.nvmlShutdown()
        return cuda_version, nv_gpus

    def probe_ollama(self) -> list[ollama.ListResponse.Model] | None:
        """Returns a list of models installed in Ollama, or None if connecting to Ollama fails."""
        with contextlib.suppress(ConnectionError):
            return list(ollama.list().models)
        return None

    def probe_ollama_version(self) -> str | None:
        """Returns the Ollama version string (e.g. "0.13.5"), or None if connecting to Ollama fails."""
        # Yes, this uses private attributes, but that lets me use the Ollama Python lib's env var logic. If you use env
        # vars to direct the app to a different Ollama server, this will query the same Ollama endpoint as the
        # ollama.list() call above. Therefore I silence SLF001 here.
        with contextlib.suppress(httpx.HTTPError, KeyError, ValueError):
            response: httpx.Response = ollama._client._client.request("GET", "/api/version")  # noqa: SLF001
            response.raise_for_status()
            return response.json()["version"]
        return None
