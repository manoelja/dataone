"""Assets estáticos convertidos para base64."""

import base64
import os


def _load_svg(filename: str) -> str:
    """Carrega um SVG da pasta public/ e retorna como base64."""
    svg_path = os.path.join(os.path.dirname(__file__), "..", "public", filename)
    if os.path.exists(svg_path):
        with open(svg_path, "r") as f:
            return base64.b64encode(f.read().encode()).decode()
    return ""


# SVGs dos ícones sociais
GITHUB_SVG = _load_svg("github.svg")
LINKEDIN_SVG = _load_svg("linkedin.svg")
PORTFOLIO_SVG = _load_svg("manoelja.svg")
