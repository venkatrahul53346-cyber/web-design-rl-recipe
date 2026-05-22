FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# uv for any agents that prefer it; the grader uses plain python.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN pip install --no-cache-dir --break-system-packages \
    "playwright==1.50.0" \
    "Pillow>=10.0,<12" \
    "numpy>=1.26,<3" \
    "scikit-image>=0.22,<0.26" \
    "beautifulsoup4>=4.12,<5"

# Bake the prompt (screenshots + instructions) into the agent's image.
COPY prompt/ /app/prompt/

# Bake task assets (e.g. placeholder images the GT references) into /app/
# so agent HTML can reference them by relative path.
COPY assets/ /app/
