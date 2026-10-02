"""Generate deterministic public-release evidence and integrity metadata.

This utility never opens a network connection or executes the demo. Run the
declared test commands first; it only packages their already-recorded output.
"""

from __future__ import annotations

import ast
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.2"
GENERATED_MANIFEST = {"RELEASE_MANIFEST.json", "SHA256SUMS.txt"}
EXCLUDED_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", "build", "dist", ".mypy_cache"}
NETWORK_IMPORTS = {"socket", "subprocess", "requests", "urllib", "http", "ftplib", "telnetlib", "webbrowser"}
SECRET_FILE_PATTERN = re.compile(r"(^|[_\-.])(secret|credential|password|private[_-]?key|token)([_\-.]|$)", re.IGNORECASE)


def canonical_hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def release_files() -> Iterable[Path]:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRECTORIES or part.startswith("_qa") for part in relative.parts):
            continue
        if relative.name in GENERATED_MANIFEST:
            continue
        yield path


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class PublicBoundaryVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] in NETWORK_IMPORTS:
                self.violations.append(f"network_or_process_import:{alias.name}:line:{node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = (node.module or "").split(".")[0]
        if module in NETWORK_IMPORTS:
            self.violations.append(f"network_or_process_import:{node.module}:line:{node.lineno}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if (node.func.value.id, node.func.attr) in {("os", "system"), ("os", "popen")}:
                self.violations.append(f"external_command_call:{node.func.value.id}.{node.func.attr}:line:{node.lineno}")
        self.generic_visit(node)


def audit_public_boundary() -> Dict[str, object]:
    violations: List[str] = []
    scanned_files: List[str] = []
    for directory in (ROOT / "src", ROOT / "tools"):
        for path in sorted(directory.rglob("*.py")):
            scanned_files.append(path.relative_to(ROOT).as_posix())
            visitor = PublicBoundaryVisitor()
            visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
            violations.extend(f"{path.relative_to(ROOT).as_posix()}:{item}" for item in visitor.violations)

    secret_paths = [path.relative_to(ROOT).as_posix() for path in release_files() if SECRET_FILE_PATTERN.search(path.name)]
    # Build the prohibited path pattern without embedding an example absolute
    # home-directory fragment in this self-auditing public tool.
    prohibited_unix_homes = "/" + "home" + "/|/" + "users" + "/"
    absolute_path_pattern = re.compile(r"(?i)(?:[a-z]:\\\\|" + prohibited_unix_homes + ")")
    absolute_path_hits = []
    for path in release_files():
        if path.suffix.lower() not in {".py", ".md", ".json", ".toml", ".cff"}:
            continue
        if absolute_path_pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            absolute_path_hits.append(path.relative_to(ROOT).as_posix())

    checks = [
        {"check": "no_network_or_external_process_import_in_public_code", "status": "PASS" if not violations else "FAIL", "evidence": violations},
        {"check": "no_secret_named_payload", "status": "PASS" if not secret_paths else "FAIL", "evidence": secret_paths},
        {"check": "no_machine_absolute_path_in_public_text_or_code", "status": "PASS" if not absolute_path_hits else "FAIL", "evidence": absolute_path_hits},
        {"check": "public_boundary_document_present", "status": "PASS" if (ROOT / "PUBLICATION_BOUNDARY.md").is_file() else "FAIL", "evidence": "PUBLICATION_BOUNDARY.md"},
    ]
    return {
        "audit_id": "G0_PUBLIC_BOUNDARY_AUDIT_V1",
        "release_version": VERSION,
        "scope": "public source, tools, declared metadata, and release payload",
        "limitations": [
            "Static audit only; it does not certify production security.",
            "No protected engineering implementation is evaluated by this audit.",
        ],
        "scanned_python_files": scanned_files,
        "checks": checks,
        "result": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
    }


def write_json(path: Path, value: object) -> None:
    write_text_lf(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_text_lf(path: Path, content: str) -> None:
    """Write release records with LF bytes on every supported host.

    Release manifests bind file bytes.  Relying on the platform default text
    newline would make a Windows-generated manifest disagree with the same
    checkout on a Unix target.
    """
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def main() -> None:
    results = ROOT / "results"
    required_results = [
        results / "fixed_cases_v0.2.2.json",
        results / "semantic_ablation_v0.2.2.json",
        results / "test_python39_v0.2.2.txt",
        results / "test_python313_v0.2.2.txt",
        results / "reproduction_environment_v0.2.2.json",
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required_results if not path.is_file()]
    if missing:
        raise SystemExit("Missing required recorded evidence: " + ", ".join(missing))

    audit = audit_public_boundary()
    write_json(ROOT / "G0_PUBLIC_BOUNDARY_AUDIT.json", audit)
    if audit["result"] != "PASS":
        raise SystemExit("G0 public-boundary audit failed; manifest was not generated.")

    entries: List[Dict[str, object]] = []
    for path in release_files():
        relative = path.relative_to(ROOT).as_posix()
        entries.append({"path": relative, "sha256": file_hash(path), "bytes": path.stat().st_size})
    manifest = {
        "schema_version": "WBSTG-RELEASE-MANIFEST-1",
        "release_name": "White Box State Transition Governance Reference Demo",
        "release_version": VERSION,
        "hash_algorithm": "SHA-256",
        "scope": "candidate-first deterministic in-memory reference demonstration",
        "excluded_payload": ["protected engineering code", "credentials", "network clients", "real executors", "production configuration"],
        "manifest_excludes": sorted(GENERATED_MANIFEST),
        "files": entries,
        "file_count": len(entries),
    }
    write_json(ROOT / "RELEASE_MANIFEST.json", manifest)

    checksum_targets = list(release_files()) + [ROOT / "RELEASE_MANIFEST.json"]
    lines = [f"{file_hash(path)}  {path.relative_to(ROOT).as_posix()}" for path in sorted(checksum_targets)]
    write_text_lf(ROOT / "SHA256SUMS.txt", "\n".join(lines) + "\n")
    print(json.dumps({"audit": audit["result"], "manifest_file_count": len(entries), "checksum_count": len(lines)}, sort_keys=True))


if __name__ == "__main__":
    main()
