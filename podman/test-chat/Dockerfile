ARG VARIANT


FROM ubuntu:24.04 AS base

# Bash supports pipefail.
SHELL ["/bin/bash", "-c"]

# Install updates and curl.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER ubuntu
WORKDIR /home/ubuntu

# Install uv and shell completions.
RUN set -eo pipefail && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc && \
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc

# Install a Python 3.12 interpreter.
RUN . /home/ubuntu/.local/bin/env; uv python install 3.12


FROM base AS pypi

COPY --chown=ubuntu:ubuntu entrypoint-pypi.sh /home/ubuntu/entrypoint.sh


FROM base AS editable

COPY --chown=ubuntu:ubuntu entrypoint-editable.sh /home/ubuntu/entrypoint.sh

WORKDIR /home/ubuntu/RAG-demo/

# This respects .dockerignore, which is a symlink to .gitignore.
COPY --chown=ubuntu:ubuntu --from=project . .


FROM ${VARIANT:-pypi} AS final

RUN chmod +x /home/ubuntu/entrypoint.sh
ENTRYPOINT ["/home/ubuntu/entrypoint.sh"]
