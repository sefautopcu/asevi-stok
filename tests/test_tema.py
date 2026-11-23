from pathlib import Path


def test_arctic_and_dark_palette_tokens_are_theme_safe():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

    assert 'border_color = "#C7D3DD"' in source
    assert 'bg_color = "#EDF3F7"' in source
    assert 'card_bg = "#FFFFFF"' in source
    assert 'sidebar_bg = "#E4EDF3"' in source
    assert 'text_color = "#102235"' in source
    assert 'subtext_color = "#52697A"' in source
    assert 'bg_color = "#040711"' in source
    assert 'card_bg = "rgba(10, 15, 29, 0.75)"' in source
    assert 'text_color = "#f4f4f5"' in source
    assert 'subtext_color = "#94a3b8"' in source


def test_dual_theme_sidebar_config_has_contrast_tokens():
    source = (
        Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"
    ).read_text(encoding="utf-8")

    assert "[theme.light.sidebar]" in source
    assert 'backgroundColor = "#e4edf3"' in source
    assert 'textColor = "#102235"' in source
    assert "[theme.dark.sidebar]" in source
    assert 'backgroundColor = "#060a14"' in source
    assert 'textColor = "#f4f4f5"' in source
