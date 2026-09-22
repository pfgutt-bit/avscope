"""Create a small deployable ZIP without the raw source or local environment."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def package(destination: Path | None = None) -> Path:
    destination = destination or ROOT.parent / "AVScope_publicacao.zip"
    roots = [ROOT / folder for folder in ("src", "scripts", "tests", "docs", ".streamlit")]
    files = [ROOT / name for name in ("app.py", "README.md", "requirements.txt", ".gitignore", ".dockerignore", "Dockerfile", "iniciar.ps1")]
    files += [ROOT / "data" / "processed" / name for name in ("avscope_mvp_domestic.parquet", "dim_airports.parquet")]
    for folder in roots:
        files.extend(path for path in folder.rglob("*") if path.is_file()
                     and "__pycache__" not in path.parts and path.name != "secrets.toml")
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(set(files)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    with ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Archive integrity check failed")
    return destination


if __name__ == "__main__":
    result = package()
    print(f"{result} ({result.stat().st_size:,} bytes)")

