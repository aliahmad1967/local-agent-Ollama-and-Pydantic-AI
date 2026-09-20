import os
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider

os.environ["PYDANTIC_AI_NO_BANNER"] = "1"
MODEL = "qwen3.8:latest"
BASE_URL = "http://localhost:11434/v1"
WORKSPACE_ROOT = Path(__file__).resolve().parent
NOTES_DIR = WORKSPACE_ROOT / "notes"

model = OllamaModel(MODEL, provider=OllamaProvider(base_url=BASE_URL))
agent = Agent(
    model,
    instructions=(
        "You are a helpful local assistant. Use the available tools when they "
        "are useful, and explain tool results clearly. Local file paths are "
        "relative to the project folder."
    ),
)


def _workspace_path(path: str) -> Path:
    candidate = (WORKSPACE_ROOT / path).resolve()
    try:
        candidate.relative_to(WORKSPACE_ROOT)
    except ValueError as error:
        raise ValueError("Path must stay inside the project folder") from error
    return candidate


class _SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str]] = []
        self._current_url = ""
        self._current_title: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and "result__a" in (attributes.get("class") or ""):
            self._current_url = attributes.get("href") or ""
            self._current_title = []

    def handle_data(self, data: str) -> None:
        if self._current_url:
            self._current_title.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_url:
            title = " ".join("".join(self._current_title).split())
            if title:
                self.results.append((title, self._current_url))
            self._current_url = ""
            self._current_title = []


@agent.tool_plain
def get_current_time() -> str:
    """Return the current time in UTC as an ISO 8601 timestamp."""
    return datetime.now(UTC).isoformat()


@agent.tool_plain
def list_files(pattern: str = "**/*") -> str:
    """List files in the project folder matching a glob pattern."""
    matches = [
        path.relative_to(WORKSPACE_ROOT).as_posix()
        for path in WORKSPACE_ROOT.glob(pattern)
        if path.is_file()
    ]
    return "\n".join(sorted(matches)[:100]) or "No matching files found."


@agent.tool_plain
def read_text_file(path: str) -> str:
    """Read a UTF-8 text file inside the project folder."""
    file_path = _workspace_path(path)
    if not file_path.is_file():
        return f"Error: file not found: {path}"
    if file_path.stat().st_size > 200_000:
        return "Error: file is larger than 200 KB"
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "Error: file is not UTF-8 text"


@agent.tool_plain
def write_note(title: str, content: str) -> str:
    """Save a Markdown note in the project's notes folder."""
    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "-", title).strip("-.")
    if not safe_title:
        return "Error: title must contain letters or numbers"
    if len(content) > 100_000:
        return "Error: note is larger than 100 KB"
    NOTES_DIR.mkdir(exist_ok=True)
    note_path = NOTES_DIR / f"{safe_title}.md"
    note_path.write_text(content, encoding="utf-8")
    return f"Saved note: {note_path.relative_to(WORKSPACE_ROOT).as_posix()}"


@agent.tool_plain
def read_pdf(path: str) -> str:
    """Extract text from a PDF inside the project folder."""
    file_path = _workspace_path(path)
    if not file_path.is_file():
        return f"Error: file not found: {path}"
    try:
        from pypdf import PdfReader
    except ImportError:
        return "Error: install the pypdf package to read PDF files"

    reader = PdfReader(str(file_path))
    pages = [page.extract_text() or "" for page in reader.pages[:20]]
    text = "\n\n".join(pages)
    return text[:100_000] or "No extractable text found in the PDF."


@agent.tool_plain
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web with DuckDuckGo and return titles and URLs."""
    if not query.strip():
        return "Error: search query cannot be empty"
    max_results = max(1, min(max_results, 10))
    request = Request(
        f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
        headers={"User-Agent": "local-ai-ollama-agent/1.0"},
    )
    with urlopen(request, timeout=10) as response:
        html = response.read().decode("utf-8", errors="replace")

    parser = _SearchResultParser()
    parser.feed(html)
    results = parser.results[:max_results]
    if not results:
        return "No search results found."
    return "\n".join(
        f"{index}. {title}\n   {url}" for index, (title, url) in enumerate(results, 1)
    )


def main() -> None:
    print("Local Ollama agent ready. Type 'exit' or 'quit' to stop.")
    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError, KeyboardInterrupt:
            print("\nGoodbye!")
            return

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            return
        if not user_input:
            continue

        try:
            result = agent.run_sync(user_input)
            print(f"Agent: {result.output}")
        except Exception as error:  # noqa: BLE001
            print(f"Agent error: {error}")


if __name__ == "__main__":
    main()
