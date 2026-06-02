from app.adapters.perplexity_agent import normalize_perplexity_model


def test_normalize_legacy_openai_model():
    assert normalize_perplexity_model("openai/gpt-4o-mini") == "openai/gpt-5-mini"
    assert normalize_perplexity_model("preset:pro-search") == "preset:pro-search"
