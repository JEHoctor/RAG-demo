FROM ubuntu:24.04

# Use bash for RUN commands to support pipefail
SHELL ["/bin/bash", "-c"]

# Install updates and curl
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create unprivileged user
RUN useradd -m -s /bin/bash user

# Switch to unprivileged user
USER user
WORKDIR /home/user

# Install uv
RUN set -eo pipefail && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc && \
    echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc

# Set up entrypoint
COPY --chown=user:user entrypoint.sh /home/user/entrypoint.sh
RUN chmod +x /home/user/entrypoint.sh

ENTRYPOINT ["/home/user/entrypoint.sh"]
