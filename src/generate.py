"""Generate Harbor-format task directories for the web-design RL benchmark.

Two entry points:

- ``generate_task(seed, ...)`` — sample a parameterised template (e.g.
  marketing), render screenshots on the host, and pack into a Harbor task
  directory.
- ``build_task_dir(out_dir, files=..., screenshots=..., ...)`` — the lower-
  level helper. Takes pre-existing HTML/CSS files + screenshots and lays out
  the same Harbor task directory shape. Used by the Design2Code ingester
  for already-frozen real-world pages.

Each task directory follows Harbor's expected layout::

    task-NNNN/
    ├── task.toml              metadata, timeouts, resource limits
    ├── instruction.md         what the agent reads
    ├── environment/
    │   ├── Dockerfile         baked agent + verifier image
    │   └── prompt/
    │       └── screenshots/   PNGs the agent sees at /app/prompt/screenshots/
    ├── solution/
    │   ├── solve.sh           oracle: copy ground truth into /app/
    │   └── ground_truth/      source HTML/CSS the oracle copies
    └── tests/
        ├── test.sh            verifier entry point
        ├── grade.py           multi-signal grader (copied from _container_grade.py)
        └── ground_truth/      HTML/CSS for grader compare; GT screenshots
                               are rendered in-container at trial time

Run a single trial with::

    harbor trial start -p datasets/<set>/<task-id> -a oracle
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Iterable, Optional

from src.render import render_site


# ---------------------------------------------------------------------------
# Static templates baked into every task directory.
# ---------------------------------------------------------------------------

# environment/Dockerfile is the agent's container. Verifier shares it (default
# Harbor mode), so playwright + the grader's Python deps are baked in here.
#
# The playwright/python:v1.50.0-noble image ships chromium binaries under
# /ms-playwright but does *not* include the playwright Python package.
# We pip-install playwright at the matching version and point it at the
# prebuilt browsers so chromium is not re-downloaded per trial.
DOCKERFILE = """\
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# uv for any agents that prefer it; the grader uses plain python.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN pip install --no-cache-dir --break-system-packages \\
    "playwright==1.50.0" \\
    "Pillow>=10.0,<12" \\
    "numpy>=1.26,<3" \\
    "scikit-image>=0.22,<0.26" \\
    "beautifulsoup4>=4.12,<5"

# Bake the prompt (screenshots + instructions) into the agent's image.
COPY prompt/ /app/prompt/

# Bake task assets (e.g. placeholder images the GT references) into /app/
# so agent HTML can reference them by relative path.
COPY assets/ /app/
"""


SOLVE_SH = """\
#!/bin/bash
# Oracle solver: copy the ground-truth website verbatim into /app/.
# Use `cp -a /dir/.` form so the copy succeeds even if a future template
# adds extra files (images, fonts) under ground_truth/.
set -euo pipefail
cp -a /solution/ground_truth/. /app/
echo "oracle: ground truth copied to /app/"
"""


TEST_SH = """\
#!/bin/bash
# Verifier entry point. Runs grade.py; falls back to reward 0 on crash.
set -uo pipefail
mkdir -p /logs/verifier

set +e
python3 /tests/grade.py 2>&1 | tee /logs/verifier/grader.log
exit_code=$?
set -e

if [ ! -f /logs/verifier/reward.json ] && [ ! -f /logs/verifier/reward.txt ]; then
    echo "WARNING: grader produced no reward file (exit $exit_code) — defaulting to 0"
    echo 0 > /logs/verifier/reward.txt
fi

exit 0
"""


# ---------------------------------------------------------------------------
# Dynamic per-task content.
# ---------------------------------------------------------------------------


def _instruction(
    pages: list[str],
    has_external_css: bool,
    placeholder_assets: Optional[list[str]] = None,
) -> str:
    """Render instruction.md for the actual page count + CSS strategy.

    Page count, file list, and CSS rule are all derived from what the task
    actually contains — no 5-page assumption.

    If ``placeholder_assets`` is non-empty, mention them in the instruction so
    the agent knows what files are pre-staged in /app/ for image references.
    """
    page_count_phrase = (
        "a single page" if len(pages) == 1 else f"a {len(pages)}-page website"
    )
    page_list = "\n".join(f"- `/app/prompt/screenshots/{p}.png`" for p in pages)
    files_list = "\n".join(f"- {p}.html" for p in pages)
    if has_external_css:
        files_list += "\n- styles.css"

    if has_external_css:
        css_rule = (
            '1. Each `.html` file must `<link rel="stylesheet" '
            'href="styles.css">`. Put all styling in `styles.css`.'
        )
    else:
        css_rule = (
            "1. CSS may be embedded in `<style>` tags inside each HTML file, "
            "or you may write a `styles.css` file and link it. Either works."
        )

    asset_note = ""
    if placeholder_assets:
        asset_lines = "\n".join(
            f"- `/app/{name}` — use as `<img src=\"{name}\">` in your HTML"
            for name in placeholder_assets
        )
        asset_note = (
            "\n## Available placeholder assets\n\n"
            "The following files are pre-staged in `/app/`. Reference them "
            "from your HTML if the design has images:\n"
            f"{asset_lines}\n"
        )

    return (
        "# Web Design Replication Task\n\n"
        f"You are given screenshots of {page_count_phrase} at "
        "`/app/prompt/screenshots/`:\n"
        f"{page_list}\n\n"
        "Recreate the design as faithfully as possible using HTML and CSS.\n\n"
        "## Required output files (write them to `/app/`)\n"
        f"{files_list}\n"
        f"{asset_note}\n"
        "## Rules\n"
        f"{css_rule}\n"
        "2. Match colours, spacing, typography, and layout structure as "
        "closely as you can.\n"
        "3. Functionality is out of scope; visual fidelity is what is graded.\n"
        "4. Do not modify or read files under `/tests/` or `/solution/`.\n"
    )


def _task_toml(
    task_name: str,
    description: str,
    metadata: Dict,
    keywords: Iterable[str] = ("web", "html", "css", "visual", "rl"),
) -> str:
    """Render task.toml. ``metadata`` is dumped as TOML key=value lines."""
    meta_lines = []
    for k, v in metadata.items():
        if isinstance(v, str):
            meta_lines.append(f'{k} = "{v}"')
        elif isinstance(v, bool):
            meta_lines.append(f"{k} = {'true' if v else 'false'}")
        else:
            meta_lines.append(f"{k} = {v}")
    metadata_block = "\n".join(meta_lines) if meta_lines else ""
    keyword_str = ", ".join(f'"{k}"' for k in keywords)

    return f"""\
schema_version = "1.1"

[task]
name = "{task_name}"
description = "{description}"
authors = []
keywords = [{keyword_str}]

[metadata]
{metadata_block}

[verifier]
timeout_sec = 600.0

[agent]
timeout_sec = 1200.0

[environment]
build_timeout_sec = 1200.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
gpus = 0
allow_internet = true
"""


# ---------------------------------------------------------------------------
# Core: build a Harbor task directory from given files + screenshots.
# ---------------------------------------------------------------------------


def build_task_dir(
    out_dir: Path,
    *,
    files: Dict[str, str],
    screenshots: Dict[str, Path],
    description: str,
    metadata: Dict,
    pages: Optional[list[str]] = None,
    task_name: Optional[str] = None,
    keywords: Iterable[str] = ("web", "html", "css", "visual", "rl"),
    bookkeeping: Optional[Dict] = None,
    assets: Optional[Dict[str, Path]] = None,
    force: bool = False,
) -> Path:
    """Lay out a Harbor task dir from already-prepared artifacts.

    Args:
        out_dir: Task root (e.g. ``datasets/web-design/task-0042``).
        files: ``{filename: content}`` — text files (HTML/CSS) written into
            both ``solution/ground_truth/`` and ``tests/ground_truth/``.
        screenshots: ``{page_stem: source_png_path}`` — copied into
            ``environment/prompt/screenshots/<page_stem>.png``.
        description: ``task.toml`` description string.
        metadata: ``[metadata]`` block in ``task.toml``.
        pages: Ordered list of page stems for the instruction. Auto-derived
            from ``files`` if None.
        task_name: ``task.name`` in ``task.toml`` (default ``out_dir.name``).
        keywords: ``task.keywords`` in ``task.toml``.
        bookkeeping: Extra fields for ``metadata.json`` (host-side only).
        assets: ``{filename: source_path}`` — binary files (images, fonts)
            written to ``environment/assets/<filename>``,
            ``solution/ground_truth/<filename>``, and
            ``tests/ground_truth/<filename>``. The Dockerfile bakes
            ``environment/assets/`` into ``/app/`` so agent HTML can
            reference these by relative path.
        force: Overwrite if ``out_dir`` already exists.
    """
    out_dir = Path(out_dir).resolve()
    if out_dir.exists():
        if not force:
            raise FileExistsError(
                f"{out_dir} already exists. Pass force=True to overwrite."
            )
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    if pages is None:
        pages = sorted(
            Path(name).stem for name in files if name.endswith(".html")
        )
    has_external_css = any(name.endswith(".css") for name in files)
    assets = assets or {}

    # 1. environment/ — Dockerfile + baked prompt screenshots + assets.
    env_dir = out_dir / "environment"
    env_prompt_screens = env_dir / "prompt" / "screenshots"
    env_prompt_screens.mkdir(parents=True)
    for stem, src in screenshots.items():
        shutil.copy2(src, env_prompt_screens / f"{stem}.png")
    # Always create assets/ so the Dockerfile's `COPY assets/ /app/` works.
    # Modal's image builder fails on a totally empty COPY source — write a
    # tiny placeholder file so the dir is never bare. Tasks that bake real
    # assets (e.g. Design2Code's rick.jpg) overlay them on top.
    env_assets = env_dir / "assets"
    env_assets.mkdir()
    (env_assets / ".harbor-keep").write_text(
        "# Placeholder — keeps environment/assets/ non-empty so Modal's "
        "image builder doesn't choke on COPY. Safe to ignore.\n"
    )
    for name, src in assets.items():
        shutil.copy2(src, env_assets / name)
    (env_dir / "Dockerfile").write_text(DOCKERFILE)

    # 2. solution/ — oracle source files + solve.sh.
    sol_gt = out_dir / "solution" / "ground_truth"
    sol_gt.mkdir(parents=True)
    for name, content in files.items():
        (sol_gt / name).write_text(content)
    for name, src in assets.items():
        shutil.copy2(src, sol_gt / name)
    solve = out_dir / "solution" / "solve.sh"
    solve.write_text(SOLVE_SH)
    solve.chmod(0o755)

    # 3. tests/ — grader + GT HTML/CSS for compare. GT screenshots are
    # rendered fresh in-container at trial time (apples-to-apples SSIM).
    tests_dir = out_dir / "tests"
    tests_gt = tests_dir / "ground_truth"
    tests_gt.mkdir(parents=True)
    for name, content in files.items():
        (tests_gt / name).write_text(content)
    for name, src in assets.items():
        shutil.copy2(src, tests_gt / name)
    test_sh = tests_dir / "test.sh"
    test_sh.write_text(TEST_SH)
    test_sh.chmod(0o755)

    grader_src = Path(__file__).resolve().parent / "_container_grade.py"
    if not grader_src.exists():
        raise FileNotFoundError(
            f"Container grader template missing at {grader_src}. "
            "Did you delete src/_container_grade.py?"
        )
    shutil.copy2(grader_src, tests_dir / "grade.py")

    # 4. instruction.md — derived from actual pages + CSS strategy + assets.
    placeholder_names = sorted(assets.keys()) if assets else None
    (out_dir / "instruction.md").write_text(
        _instruction(pages, has_external_css, placeholder_names)
    )

    # 5. task.toml — derived from name + description + metadata.
    name = task_name or f"web-design/{out_dir.name}"
    (out_dir / "task.toml").write_text(
        _task_toml(name, description, metadata, keywords=keywords)
    )

    # 6. metadata.json — host-side bookkeeping (not consumed by Harbor).
    if bookkeeping is None:
        bookkeeping = {}
    bookkeeping = {
        **bookkeeping,
        "pages": pages,
        "files": sorted(files.keys()),
        "has_external_css": has_external_css,
        "assets": sorted(assets.keys()) if assets else [],
    }
    (out_dir / "metadata.json").write_text(json.dumps(bookkeeping, indent=2))

    return out_dir


# ---------------------------------------------------------------------------
# Template-driven generator (current marketing template).
# ---------------------------------------------------------------------------


def generate_task(*args, **kwargs) -> Path:
    """Removed.

    The v0 ``generate_task`` entry point built tasks from the legacy
    ``templates.marketing`` module (deterministic HTML emitter, no LLM).
    Phase 2's ``src.synthesize.synthesize_task`` replaces it; the legacy
    template is archived under ``_archive/templates/_legacy_marketing.py``.
    """
    raise RuntimeError(
        "generate_task() was removed when the v0 marketing template was "
        "archived. Use `python -m src.synthesize --template <name> --seed N "
        "--out <dir>` instead. See REPORT.md for details."
    )


def main() -> None:
    raise SystemExit(
        "src.generate is no longer a user-facing CLI. Run "
        "`python -m src.synthesize --help` for the current entry point."
    )


if __name__ == "__main__":
    main()
