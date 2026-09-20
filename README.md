# Local Ollama Agent

A local Python chat agent powered by Ollama and Pydantic AI. It uses the
`qwen3.8:latest` model and can work with project files, notes, PDFs, and web
searches.

## Requirements

- Windows PowerShell
- Python 3.14 or later
- [Ollama](https://ollama.com/download/windows)
- [`uv`](https://docs.astral.sh/uv/)

## Setup

From the project folder:

```powershell
uv sync
ollama pull qwen3.8:latest
```

Ollama normally runs as a background service. Check that it is available:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

If Ollama is not running, start it in a separate terminal:

```powershell
ollama serve
```

If you see `bind: Only one usage of each socket address`, Ollama is already
running. Do not start a second server.

## Run

```powershell
uv run python .\main.py
```

Then type a request at the `You:` prompt. Type `exit` or `quit` to stop.

Example:

```text
You: what is the date now
You: list the Python files in this project
You: save a note titled meeting with the text Follow up tomorrow
You: search the web for the latest Python release
```

## Available Tools

- `get_current_time`: returns the current UTC time.
- `list_files`: lists project files matching a glob pattern.
- `read_text_file`: reads UTF-8 text files in the project folder.
- `write_note`: saves Markdown notes in the `notes` folder.
- `read_pdf`: extracts text from up to 20 pages of a PDF in the project folder.
- `web_search`: searches DuckDuckGo and returns result titles and URLs.

File tools only access paths inside the project folder. Text and note results
are size-limited, and PDF extraction returns at most 100,000 characters.

## Development Checks

Run the linter with:

```powershell
uv run ruff check .\main.py
```

The project uses Ruff's isort-compatible import checks when needed:

```powershell
uv run ruff check --select I .\main.py
```
