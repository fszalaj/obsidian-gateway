"""Optional broad-language pass via tree-sitter-language-pack (the [graph-all] extra).

One dependency covers many languages (JS/TS/Go/Rust/Java/C#/PHP/Ruby/bash/PowerShell/
Terraform/...). If the package is not installed, AVAILABLE is False and the build simply
skips these languages - the Python (ast) and Ansible (yaml) passes need no tree-sitter.

Adding a language later = one line in EXT_LANG (data, not a rewrite).
"""
from __future__ import annotations

from pathlib import Path

try:  # the broad pass is opt-in; core install stays light
    from tree_sitter_language_pack import get_parser
    AVAILABLE = True
except Exception:  # pragma: no cover - exercised only with the [graph-all] extra
    AVAILABLE = False

# extension -> tree-sitter language name. Extend freely; coverage is data, not code.
EXT_LANG = {
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx",
    ".go": "go", ".rs": "rust", ".java": "java", ".cs": "c_sharp",
    ".rb": "ruby", ".php": "php", ".sh": "bash", ".bash": "bash",
    ".ps1": "powershell", ".psm1": "powershell",
    ".tf": "hcl", ".tfvars": "hcl", ".hcl": "hcl",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".lua": "lua", ".kt": "kotlin", ".swift": "swift", ".scala": "scala",
}
LANG_EXTS = set(EXT_LANG)

# tree-sitter node types that denote a definition, across grammars (heuristic, language-agnostic).
_DEF_TYPES = {
    "function_declaration", "function_definition", "function_item", "method_definition",
    "method_declaration", "function", "method", "arrow_function", "func_literal",
    "class_declaration", "class_definition", "class_specifier", "class", "struct_item",
    "struct_specifier", "interface_declaration", "type_declaration", "module",
    "block",  # terraform/hcl resource/module blocks
}
_NAME_TYPES = ("identifier", "name", "type_identifier", "field_identifier",
               "constant", "word", "string_literal")


def _name(node, src: bytes) -> str | None:
    for ch in node.children:
        if ch.type in _NAME_TYPES:
            return src[ch.start_byte:ch.end_byte].decode("utf-8", "replace").strip('"').strip()
    return None


def extract(path: Path, rel: str) -> dict:
    if not AVAILABLE:
        return {"nodes": [], "edges": []}
    lang = EXT_LANG.get(path.suffix.lower())
    if not lang:
        return {"nodes": [], "edges": []}
    try:
        parser = get_parser(lang)
        src = path.read_bytes()
        tree = parser.parse(src)
    except Exception:
        return {"nodes": [], "edges": []}

    nodes: list[dict] = []
    edges: list[dict] = []
    mod = f"module:{rel}"
    nodes.append({"id": mod, "label": rel, "type": "module", "file_type": lang, "source_file": rel})

    stack = [tree.root_node]
    seen: set[str] = set()
    while stack:
        n = stack.pop()
        if n.type in _DEF_TYPES:
            nm = _name(n, src)
            if nm:
                nid = f"{lang}:{rel}:{nm}:L{n.start_point[0] + 1}"
                if nid not in seen:
                    seen.add(nid)
                    kind = "class" if "class" in n.type or "struct" in n.type or "interface" in n.type else "function"
                    nodes.append({"id": nid, "label": nm, "type": kind, "file_type": lang,
                                  "source_file": rel, "source_location": f"L{n.start_point[0] + 1}"})
                    edges.append({"source": mod, "target": nid, "relation": "defines", "confidence": "EXTRACTED"})
        stack.extend(n.children)
    return {"nodes": nodes, "edges": edges}
