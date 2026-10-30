import json
import tempfile
import unittest
from pathlib import Path

from scripts.setup_es import DATASETS, ROOT, bulk_lines, convert_to_bulk, read_documents


class DatasetTests(unittest.TestCase):
    def test_document_counts_and_unique_ids(self):
        for index_name, path in DATASETS.items():
            with self.subTest(index=index_name):
                documents = list(read_documents(path))
                self.assertEqual(len(documents), 10000 if index_name == "weibo_hot_search" else 20000)
                self.assertEqual(len({document["id"] for document in documents}), len(documents))

    def test_mapping_covers_every_dataset_field(self):
        for index_name, path in DATASETS.items():
            mapping_name = "mapping_hot_search.json" if index_name == "weibo_hot_search" else "mapping_user_behavior.json"
            mapping = json.loads((ROOT / "config" / mapping_name).read_text(encoding="utf-8"))
            first = next(read_documents(path))
            self.assertLessEqual(set(first), set(mapping["mappings"]["properties"]))


class BulkTests(unittest.TestCase):
    def test_bulk_contract(self):
        documents = [{"id": "hs_1", "title": "测试"}]
        lines = list(bulk_lines(documents, "weibo_hot_search"))
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["index"]["_id"], "hs_1")
        self.assertEqual(json.loads(lines[1])["title"], "测试")

    def test_full_bulk_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            for index_name, source in DATASETS.items():
                target = Path(directory) / f"{index_name}.ndjson"
                count = convert_to_bulk(source, index_name, target)
                with target.open(encoding="utf-8") as bulk_file:
                    self.assertEqual(sum(1 for _ in bulk_file), count * 2)


class PostmanTests(unittest.TestCase):
    def test_collection_and_raw_bodies_are_valid(self):
        collection = json.loads((ROOT / "postman" / "weibo_hotsearch.postman_collection.json").read_text(encoding="utf-8"))
        requests = []

        def walk(items):
            for item in items:
                if "item" in item:
                    walk(item["item"])
                elif "request" in item:
                    requests.append(item)

        walk(collection["item"])
        self.assertEqual(len(requests), 39)
        for item in requests:
            raw = item["request"].get("body", {}).get("raw")
            if raw:
                with self.subTest(request=item["name"]):
                    json.loads(raw)


if __name__ == "__main__":
    unittest.main()
