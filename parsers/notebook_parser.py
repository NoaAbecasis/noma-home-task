import json


def extract_cell_sources(raw: str) -> list[str]:
    """Return joined source text for every code cell in a Jupyter notebook."""
    notebook = json.loads(raw)  # raises json.JSONDecodeError on bad input
    sources = []
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        text = "".join(source) if isinstance(source, list) else source
        if text:
            sources.append(text)
    return sources
