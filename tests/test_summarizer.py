import pytest

from kit.summaries import Summarizer, LLMError


class FakeRepo:
    """Minimal fake Repository with in-memory file storage."""

    def __init__(self, files):
        self._files = files

    def get_file_content(self, path: str) -> str:
        if path not in self._files:
            raise FileNotFoundError(path)
        return self._files[path]


# --- Helper fake OpenAI client --------------------------------------------

class _FakeCompletion:
    def __init__(self, content: str):
        # Mimic OpenAI response object shape we access in Summarizer
        self.choices = [type("_Choice", (), {"message": type("_Msg", (), {"content": content})()})]


class _FakeChatCompletions:
    def __init__(self, content: str, raise_exc: bool = False):
        self._content = content
        self._raise = raise_exc

    def create(self, *args, **kwargs):  # noqa: D401
        if self._raise:
            raise RuntimeError("API down")
        return _FakeCompletion(self._content)


class FakeOpenAI:
    """Mimics the parts of openai.OpenAI used by Summarizer."""

    def __init__(self, summary: str = "Fake summary", raise_exc: bool = False):
        self.chat = type("_Chat", (), {"completions": _FakeChatCompletions(summary, raise_exc)})()


# ---------------------------------------------------------------------------


def test_summarize_file_happy():
    repo = FakeRepo({"foo.py": "print('hello')"})
    client = FakeOpenAI("This file prints hello")
    summarizer = Summarizer(repo, llm_client=client)
    summary = summarizer.summarize_file("foo.py")
    assert summary == "This file prints hello"


def test_summarize_file_not_found():
    repo = FakeRepo({})
    summarizer = Summarizer(repo, llm_client=FakeOpenAI())
    with pytest.raises(FileNotFoundError):
        summarizer.summarize_file("missing.py")


def test_summarize_llm_error():
    repo = FakeRepo({"bar.py": "print('x')"})
    error_client = FakeOpenAI(raise_exc=True)
    summarizer = Summarizer(repo, llm_client=error_client)
    with pytest.raises(LLMError):
        summarizer.summarize_file("bar.py")
