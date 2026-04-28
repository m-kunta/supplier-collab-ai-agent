from __future__ import annotations

import unittest
from pathlib import Path

from api.deps import PROJECT_ROOT, resolve_data_dir


class ResolveDataDirTests(unittest.TestCase):
    def test_resolve_data_dir_keeps_absolute_paths(self) -> None:
        path = Path("/tmp/supplier-collab-test")
        self.assertEqual(resolve_data_dir(str(path)), path)

    def test_resolve_data_dir_anchors_relative_paths_to_project_root(self) -> None:
        resolved = resolve_data_dir("data/inbound/mock")
        self.assertEqual(resolved, PROJECT_ROOT / "data/inbound/mock")
