from __future__ import annotations

import contextlib
import platform
from pathlib import Path

import cpuinfo
import httpx
import huggingface_hub
import ollama
import psutil
import pynvml
from huggingface_hub.constants import HF_HUB_CACHE

try:
    # llama-cpp-python is an optional dependency. If it is not installed in the dev environment then we need to ignore
    # unresolved-import. If it is installed, then we need to ignore unused-ignore-comment (because there is no need to
    # ignore unresolved-import in this case).
    import llama_cpp  # ty:ignore[unresolved-import, unused-ignore-comment]

    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False


def probe_os() -> str:
    """Returns the OS name (eg 'Linux' or 'Windows'), the system name (eg 'Java'), or an empty string if unknown."""
    return platform.system()


def probe_architecture() -> str:
    """Returns the machine architecture, such as 'i386'."""
    return platform.machine()


def probe_cpu() -> str:
    """Returns the name of the CPU, e.g. "Intel(R) Core(TM) i7-10610U CPU @ 1.80GHz"."""
    return cpuinfo.get_cpu_info()["brand_raw"]


def probe_ram() -> int:
    """Returns the total amount of RAM in bytes."""
    return psutil.virtual_memory().total


def probe_disk_space() -> int:
    """Returns the amount of free space in the root directory (in bytes)."""
    return psutil.disk_usage("/").free


def probe_llama_available() -> bool:
    """Returns True if llama-cpp-python is installed, False otherwise."""
    return LLAMA_AVAILABLE


def probe_llamacpp_gpu_support() -> bool:
    """Returns True if the installed version of llama-cpp-python supports GPU offloading, False otherwise."""
    return LLAMA_AVAILABLE and llama_cpp.llama_supports_gpu_offload()


def probe_huggingface_free_cache_space() -> int | None:
    """Returns the amount of free space in the Hugging Face cache (in bytes), or None if it can't be determined."""
    with contextlib.suppress(FileNotFoundError):
        return psutil.disk_usage(HF_HUB_CACHE).free
    for parent_dir in Path(HF_HUB_CACHE).parents:
        with contextlib.suppress(FileNotFoundError):
            return psutil.disk_usage(str(parent_dir)).free
    return None


def probe_huggingface_cached_models() -> list[huggingface_hub.CachedRepoInfo] | None:
    """Returns a list of models in the Hugging Face cache (possibly empty), or None if the cache doesn't exist."""
    # The docstring for huggingface_hub.scan_cache_dir says it raises CacheNotFound "if the cache directory does not
    # exist," and ValueError "if the cache directory is a file, instead of a directory."
    with contextlib.suppress(ValueError, huggingface_hub.CacheNotFound):
        return [repo for repo in huggingface_hub.scan_cache_dir().repos if repo.repo_type == "model"]
    return None  # Isn't it nice to be explicit?


def probe_huggingface_cached_datasets() -> list[huggingface_hub.CachedRepoInfo] | None:
    """Returns a list of datasets in the Hugging Face cache (possibly empty), or None if the cache doesn't exist."""
    with contextlib.suppress(ValueError, huggingface_hub.CacheNotFound):
        return [repo for repo in huggingface_hub.scan_cache_dir().repos if repo.repo_type == "dataset"]
    return None


def probe_nvidia() -> tuple[int, list[str]]:
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


def probe_ollama() -> list[ollama.ListResponse.Model] | None:
    """Returns a list of models installed in Ollama, or None if connecting to Ollama fails."""
    with contextlib.suppress(ConnectionError):
        return list(ollama.list().models)
    return None


def probe_ollama_version() -> str | None:
    """Returns the Ollama version string (e.g. "0.13.5"), or None if connecting to Ollama fails."""
    # Yes, this uses private attributes, but that lets me use the Ollama Python lib's env var logic. If you use env
    # vars to direct the app to a different Ollama server, this will query the same Ollama endpoint as the
    # ollama.list() call above. Therefore I silence SLF001 here.
    with contextlib.suppress(httpx.HTTPError, KeyError, ValueError):
        response: httpx.Response = ollama._client._client.request("GET", "/api/version")  # noqa: SLF001
        response.raise_for_status()
        return response.json()["version"]
    return None
