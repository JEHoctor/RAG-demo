FROM ubuntu:24.04

# Use bash for RUN commands to support pipefail
SHELL ["/bin/bash", "-c"]

# Install updates and curl
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switch to unprivileged user
USER ubuntu
WORKDIR /home/ubuntu

# Install uv
RUN set -eo pipefail && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc && \
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc

# Get a Python 3.12 interpreter so we don't have to download it when we run uv in the container.
RUN . /home/ubuntu/.local/bin/env; uv python install 3.12

# Set up entrypoint
COPY --chown=ubuntu:ubuntu entrypoint.sh /home/ubuntu/entrypoint.sh
RUN chmod +x /home/ubuntu/entrypoint.sh

ENTRYPOINT ["/home/ubuntu/entrypoint.sh"]
