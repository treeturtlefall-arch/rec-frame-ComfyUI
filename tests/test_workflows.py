"""ワークフロー JSON の整合性検証テスト。"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"


class TestWorkflowFiles(unittest.TestCase):
    def test_workflow_files_exist_and_valid(self):
        expected_files = [
            "rec_frame_basic_workflow_en.json",
            "rec_frame_basic_workflow_ja.json",
            "rec_frame_2000s_digicam_workflow_en.json",
            "rec_frame_2000s_digicam_workflow_ja.json",
            "rec_frame_video_batch_workflow_en.json",
            "rec_frame_video_batch_workflow_ja.json",
        ]
        for name in expected_files:
            file_path = WORKFLOWS_DIR / name
            self.assertTrue(file_path.is_file(), f"Workflow file not found: {name}")

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 必須トップレベルキーの確認
            for key in ["id", "nodes", "links", "groups", "version"]:
                self.assertIn(key, data, f"Missing key '{key}' in {name}")

            # ノード検証
            node_ids = {node["id"] for node in data["nodes"]}
            has_rec_node = False
            for node in data["nodes"]:
                self.assertIn("type", node)
                self.assertIn("pos", node)
                self.assertIn("size", node)
                if node["type"] in ("RecFrameImageOverlay", "RecFrameVideoOverlay", "RecFrameOverlay"):
                    has_rec_node = True
                    # ウィジェット数とnamedの確認
                    self.assertIn("widgets_values", node)
                    self.assertIn("widgets_values_named", node)
                    self.assertIn("retro_effect", node["widgets_values_named"])
                    if node["type"] == "RecFrameImageOverlay":
                        # 静止画用: 19個 (override_* 撤廃、retro_effect に集約)
                        self.assertEqual(len(node["widgets_values"]), 19)
                    elif node["type"] in ("RecFrameVideoOverlay", "RecFrameOverlay"):
                        # 動画用/旧統合: 21個
                        self.assertEqual(len(node["widgets_values"]), 21)
                        if node["type"] == "RecFrameVideoOverlay":
                            named_keys = list(node["widgets_values_named"].keys())
                            dot_idx = named_keys.index("custom_dot_path")
                            blink_idx = named_keys.index("blink_red_dot_interval")
                            fps_idx = named_keys.index("advance_timecode_fps")
                            self.assertEqual(blink_idx, dot_idx + 1, "blink_red_dot_interval must be directly under custom_dot_path")
                            self.assertEqual(fps_idx, dot_idx + 2, "advance_timecode_fps must be directly under blink_red_dot_interval")

            self.assertTrue(has_rec_node, f"REC Overlay node not found in {name}")

            # リンク整合性の確認: [link_id, from_node, from_slot, to_node, to_slot, type]
            for link in data["links"]:
                link_id, from_node, from_slot, to_node, to_slot, link_type = link
                self.assertIn(from_node, node_ids, f"Link {link_id} from invalid node {from_node} in {name}")
                self.assertIn(to_node, node_ids, f"Link {link_id} to invalid node {to_node} in {name}")


if __name__ == "__main__":
    unittest.main()
