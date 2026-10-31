"""Build and verify a reproducible resource-pack ZIP from pack/."""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "pack"
OUTPUT = ROOT / "dist/create-style-hnn-1.0.0.zip"
STAMP = (2020, 1, 1, 0, 0, 0)
SUFFIXES = {".json", ".png", ".mcmeta", ".obj", ".mtl", ".txt"}


def archive_bytes() -> bytes:
    rows = []
    for path in sorted(SOURCE.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not packaged")
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE).as_posix()
        if path.suffix not in SUFFIXES or any(part.startswith(".") for part in Path(relative).parts):
            raise ValueError(f"Unexpected resource: {relative}")
        raw = path.read_bytes()
        if path.suffix in {".json", ".mcmeta"}:
            json.loads(raw)
        rows.append((relative, raw))
    if "pack.mcmeta" not in dict(rows):
        raise ValueError("Missing pack.mcmeta")
    memory = BytesIO()
    with ZipFile(memory, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, raw in rows:
            info = ZipInfo(name, date_time=STAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, raw, compress_type=ZIP_DEFLATED, compresslevel=9)
    data = memory.getvalue()
    with ZipFile(BytesIO(data)) as archive:
        if archive.testzip() is not None or archive.namelist() != [name for name, _ in rows]:
            raise ValueError("Archive validation failed")
        for name, raw in rows:
            if archive.read(name) != raw:
                raise ValueError(f"Archive content differs: {name}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the existing ZIP against current sources")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    data = archive_bytes()
    output = args.output.resolve()
    if args.check:
        if output.read_bytes() != data:
            raise ValueError("Existing ZIP differs from current sources")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        (output.parent / "SHA256SUMS").write_text(
            f"{hashlib.sha256(data).hexdigest()}  {output.name}\n", encoding="utf-8")
    print(json.dumps({"archive": output.name, "sha256": hashlib.sha256(data).hexdigest(),
                      "bytes": len(data), "verified": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
