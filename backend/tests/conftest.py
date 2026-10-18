import pytest

from backend.main import create_app


class FakeLLM:
    """Stands in for LLMService; complete() echoes so summarising plugins can be tested."""

    def __init__(self, provider=None):
        self._provider = provider

    def provider_name(self):
        return "fake"

    def configured(self):
        return True

    def provider(self):
        return self._provider

    async def complete(self, prompt, system="", images=None):
        return f"SUMMARY({len(prompt)})" + (" +image" if images else "")


@pytest.fixture
def app():
    a = create_app("sqlite://", start_plugins=False)
    a.state.ctx.llm = FakeLLM()
    return a


@pytest.fixture
def ctx(app):
    return app.state.ctx


@pytest.fixture
def reg(ctx):
    return ctx.registry


@pytest.fixture
def approve(ctx, monkeypatch):
    async def yes(title, details=None):
        return True
    monkeypatch.setattr(ctx.confirm, "request", yes)
