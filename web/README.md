# Markdrop web library

Self-hosted UI for this fork. Drop PDFs into a book shelf, convert them on the server, and read the Markdown. The `markdrop/` package is unchanged so you can keep merging upstream.

Open **http://localhost:8080** after the container is up. Data (library, settings, API keys, model cache) lives in the `markdrop-data` Docker volume.

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/) with Compose v2 (`docker compose`)
- **RAM:** about 8 GB for normal (Docling) convert, 4 GB for `lite` / fast convert
- Optional: Python 3.10+ only if you run without Docker

Jobs convert **one PDF at a time**. Extra drops sit in `queued` until the current worker exits.

---

## Configure

From the repo root, copy the example env file and edit it:

| Variable | Default | Meaning |
|---|---|---|
| `MARKDROP_ENGINE` | `full` | `full` = Docling + CPU Torch (normal convert). `lite` = PyMuPDF only, smaller image. |
| `MARKDROP_EXTRAS` | `lite,litellm` | Same extras as `pip install "markdrop[lite,litellm]"`. |
| `MARKDROP_WEB_PORT` | `8080` | Host port. |
| `MARKDROP_WEB_PASSWORD` | *(empty)* | If set, the UI asks for this password. |

Same install you already used locally: `ENGINE=full` and `EXTRAS=lite,litellm`.

Optional RAM caps (kill the container if it grows past the limit; they do not shrink Docker Desktop / WSL):

```
MARKDROP_MEM_LIMIT=2g
MARKDROP_SHM_SIZE=64m
```

---

## Run with Docker

### Linux

```bash
cp .env.example .env
nano .env    # or whatever editor you use
docker compose up --build
```

Detached: `docker compose up --build -d`. Stop: `Ctrl+C` or `docker compose down`.

Prefix env vars if you prefer not to use a `.env` file:

```bash
MARKDROP_ENGINE=full MARKDROP_EXTRAS=lite,litellm docker compose up --build

# Smaller image, fast convert only
MARKDROP_ENGINE=lite MARKDROP_EXTRAS=lite,litellm docker compose up --build
```

---

### Windows (Docker Desktop)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) with the **WSL 2** engine.
2. Settings → Resources: **8 GB RAM** for `full`, **4 GB** is enough for `lite`.
3. PowerShell, from the repo root:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose up --build
```

Edit `.env` instead of prefixing variables (PowerShell does not use `VAR=value command` syntax):

```
MARKDROP_ENGINE=full
MARKDROP_EXTRAS=lite,litellm
MARKDROP_WEB_PORT=8080
# MARKDROP_WEB_PASSWORD=pick-a-password
```

For the smaller image, set `MARKDROP_ENGINE=lite` in `.env`, then `docker compose up --build` again.

Stop with `Ctrl+C`, or `docker compose up --build -d` then `docker compose down`.

Idle RAM on Windows is mostly the Docker Desktop / WSL2 VM. To cap WSL, put this in `%UserProfile%\.wslconfig` and run `wsl --shutdown`:

```
[wsl2]
memory=3GB
```

---

## Rebuild / troubleshooting

First **normal** convert downloads Docling models into `/data/cache` on the volume.

If convert fails with `operator torchvision::nms does not exist`, the image has a CPU/CUDA torch mismatch. Rebuild with no cache:

Linux:

```bash
docker compose build --no-cache && docker compose up
```

Windows (PowerShell):

```powershell
docker compose build --no-cache
docker compose up
```

---

## Local (no Docker)

The UI is React (`web/frontend`). Docker builds it into the image. For live UI work, run the API, then Vite.

### Linux / macOS

```bash
pip install -e ".[lite,litellm]"
pip install -r web/requirements.txt
export MARKDROP_DATA_DIR=./data
python -m web
```

Then, in another terminal:

```bash
cd web/frontend
npm install
npm run dev
```

Vite proxies `/api` to port 8080.

---

### Windows (PowerShell)

Python 3.10+:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[lite,litellm]"
pip install -r web\requirements.txt
$env:MARKDROP_DATA_DIR = "$PWD\data"
python -m web
```

If `Activate.ps1` is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

Then `cd web\frontend`, `npm install`, `npm run dev`.

Docker is still easier on Windows because Docling/Torch is a large install.

---

## Layout on disk

```
data/library/<book-id>/
  book.json
  source/<name>.pdf
  cover.jpg
  out/                 # zip download is this folder
```

Settings: `data/settings.json`. API keys: `data/config/markdrop/.env`.

The Markdown reader renders on the server (Python `markdown` + `bleach`).
