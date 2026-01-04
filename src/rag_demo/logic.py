from __future__ import annotations

import asyncio
import contextlib
import platform
import pprint
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, cast

import aiosqlite
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
from langchain_core.exceptions import LangChainException
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_demo import dirs
from rag_demo.modes.chat import Response, StoppedStreamError

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from rag_demo.app import RAGDemo
    from rag_demo.modes import ChatScreen


class Logic:
    """Top-level application logic."""

    def __init__(
        self,
        username: str | None = None,
        application_start_time: float | None = None,
        sqlite_connection_string: str = f"sqlite:///{dirs.DATA_DIR}/checkpoints.sqlite3",
    ) -> None:
        """Initialize the application logic.

        Args:
            username (str | None, optional): The username provided as a command line argument. Defaults to None.
            application_start_time (float | None, optional): The time when the application started. Defaults to None.
            sqlite_connection_string (str, optional): The connection string for the SQLite database. Defaults to
                f"sqlite:///{dirs.DATA_DIR}/checkpoints.sqlite3".
        """
        start_time = time.time()
        self.logic_init_times = {}
        if application_start_time is not None:
            self.logic_init_times["before logic initializes"] = start_time - application_start_time
        self.username = username
        self.application_start_time = application_start_time
        self.sqlite_connection_string = sqlite_connection_string
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

        llm_done_time = time.time()
        self.logic_init_times["llm probing and init"] = llm_done_time - start_time

        # TODO: Do I need to set check_same_thread=False?
        # self._conn = aiosqlite.connect(database=dirs.DATA_DIR / "checkpoints.sqlite3", check_same_thread=False)
        self.agent: CompiledStateGraph | None = None
        self.current_thread = 1

        # Slow. Commented out for now. Should be moved to some async task perhaps.
        # # RAG:
        # self.qa_test: Dataset = cast(
        #     "Dataset",
        #     load_dataset("rag-datasets/rag-mini-wikipedia", "question-answer", split="test"),
        # )
        # self.corpus: Dataset = cast(
        #     "Dataset",
        #     load_dataset("rag-datasets/rag-mini-wikipedia", "text-corpus", split="passages"),
        # )

        datasets_done_time = time.time()
        self.logic_init_times["datasets loading"] = datasets_done_time - llm_done_time
        self.logic_init_times["total"] = datasets_done_time - start_time

        self.generating = False

    async def main_worker(self, app: RAGDemo) -> None:
        async with aiosqlite.connect(database=self.sqlite_connection_string) as conn:
            await self._main_worker(app, conn)

    async def _main_worker(self, app: RAGDemo, conn: aiosqlite.Connection) -> None:
        pass

    async def async_init(self) -> None:
        async_init_start_time = time.time()
        self.agent = create_agent(
            model=self.llm,
            system_prompt="You are a helpful assistant.",
            # checkpointer=AsyncSqliteSaver(self._conn),
        )
        self.logic_init_times["agent init"] = time.time() - async_init_start_time

    def new_conversation(self, chat_screen: ChatScreen) -> None:
        self.current_thread += 1
        chat_screen.clear_chats()

    async def submit_request(self, chat_screen: ChatScreen, request_text: str) -> bool:
        if self.generating:
            return False
        self.generating = True
        chat_screen.new_request(request_text)
        response = chat_screen.new_response()
        chat_screen.run_worker(self.stream_response(response, request_text, str(self.current_thread)))
        self.generating = False
        return True

    async def stream_response(self, response_widget: Response, request_text: str, thread: str) -> None:
        """Worker method for streaming tokens from the active agent to a response widget.

        Args:
            response_widget (Response): Target response widget for streamed tokens.
            request_text (str): Text of the user request.
        """
        if self.agent is None:
            raise RuntimeError("Agent is not initialized")  # noqa: EM101
        async with response_widget.stream_writer() as writer:
            agent_stream = self.agent.astream(
                # agent_stream = self.agent.stream(
                {"messages": [HumanMessage(content=request_text)]},
                {"configurable": {"thread_id": thread}},
                stream_mode="messages",
            )
            try:
                # for chunk in agent_stream:
                async for chunk in agent_stream:
                    # content = str(len(chunk["model"]["messages"]))
                    content = pprint.pformat(chunk)
                    if not isinstance(content, str):
                        response_widget.log.error(
                            f"Received non-string response from agent of type {type(chunk.content)}"
                        )
                        continue
                    response_widget.log.info(content)
                    await writer.write(content)
            except StoppedStreamError as e:
                # response_widget.notify(f"Stopped by user: {e}")
                response_widget.set_shown_object(e)
            except LangChainException as e:
                # response_widget.notify(f"Error: {e}")
                response_widget.set_shown_object(e)
            # finally:
            # await agent_stream.aclose()

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
