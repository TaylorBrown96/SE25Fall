# ---- Base: Python devcontainer (Ubuntu + Python + dev utils + 'vscode' user)
FROM mcr.microsoft.com/devcontainers/python:3.11

# ---- Global env (quiet, deterministic)
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PNPM_HOME=/usr/local/share/pnpm \
    PATH=/usr/local/share/pnpm:$PATH

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl ca-certificates gnupg git openssh-client \
      build-essential pkg-config \
 && rm -rf /var/lib/apt/lists/*

ARG NODE_MAJOR=20
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && corepack enable \
 && corepack prepare pnpm@9.12.0 --activate \
 && npm -v && node -v && pnpm -v

WORKDIR /workspaces
RUN mkdir -p /workspaces && chown -R vscode:vscode /workspaces

USER vscode
RUN python -m venv /home/vscode/.venv
ENV PATH=/home/vscode/.venv/bin:$PATH

RUN pip install --upgrade pip setuptools wheel

RUN mkdir -p /home/vscode/.cache/pip /home/vscode/.cache/pnpm
