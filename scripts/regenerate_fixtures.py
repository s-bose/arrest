#!/usr/bin/env python3
"""Regenerate OpenAPI test fixtures after upgrading datamodel-code-generator."""

import os
import tempfile
from pathlib import Path

from arrest.openapi import OpenAPIGenerator

FIXTURE_PATH = Path("tests/fixtures")
GENERATED_PATH = FIXTURE_PATH / "generated"

inputs = [
    ("v3", "openapi_petstore.json"),
    ("v3_schema_long_name", "openapi_petstore_schema_long_name.json"),
    ("v3.1", "openapi_petstore_3.1.json"),
    ("v3.1_with_root", "openapi_petstore_3.1_with_root.json"),
    ("v3", "openapi_petstore.yaml"),
    ("v3.1", "openapi_petstore_3.1.yaml"),
]

for gen_dir, fixture_file in inputs:
    filepath = FIXTURE_PATH / fixture_file
    target_dir = GENERATED_PATH / gen_dir

    with tempfile.TemporaryDirectory() as tmp:
        gen = OpenAPIGenerator(url=str(filepath), output_path=tmp)
        gen.generate_schema(silent=True)

        walk_root, dirs, _ = next(os.walk(tmp))
        src_dir = Path(walk_root) / dirs[0] if dirs else Path(walk_root)

        for fname in ["__init__.py", "models.py", "resources.py", "services.py"]:
            src_file = src_dir / fname
            if src_file.exists():
                (target_dir / fname).write_text(src_file.read_text())

print(f"Generated {len(inputs)} fixtures in {GENERATED_PATH!s}")
