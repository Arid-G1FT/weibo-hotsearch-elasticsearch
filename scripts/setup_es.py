import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"
DATASETS = {
    "weibo_hot_search": DATA_DIR / "weibo_hot_search.json",
    "user_behavior": DATA_DIR / "user_behavior.json",
}
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200").rstrip("/")


class ESRequestError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(f"Elasticsearch HTTP {status}：{message}")
        self.status = status


def read_documents(path):
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path.name} 第 {line_number} 行不是有效 JSON") from exc


def bulk_lines(documents, index_name):
    for document in documents:
        yield json.dumps({"index": {"_index": index_name, "_id": document["id"]}}, ensure_ascii=False)
        yield json.dumps(document, ensure_ascii=False)


def convert_to_bulk(input_path, index_name, output_path):
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as target:
        for document in read_documents(input_path):
            target.write(json.dumps({"index": {"_index": index_name, "_id": document["id"]}}, ensure_ascii=False) + "\n")
            target.write(json.dumps(document, ensure_ascii=False) + "\n")
            count += 1
    return count


def request(method, path, payload=None, content_type="application/json", expected=(200, 201)):
    body = None if payload is None else (payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    req = urllib.request.Request(f"{ES_HOST}{path}", data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as exc:
        content = exc.read().decode("utf-8", errors="replace")
        if exc.code in expected:
            return json.loads(content) if content else {}
        raise ESRequestError(exc.code, content[:1000]) from exc
    except urllib.error.URLError as exc:
        raise ConnectionError(f"无法连接 {ES_HOST}：{exc.reason}") from exc


def wait_for_es(timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            request("GET", "/")
            return
        except (ConnectionError, ESRequestError):
            time.sleep(2)
    raise TimeoutError(f"等待 Elasticsearch 就绪超时（{timeout} 秒）")


def create_index(index_name):
    mapping_path = CONFIG_DIR / f"mapping_{'hot_search' if index_name == 'weibo_hot_search' else 'user_behavior'}.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    result = request("PUT", f"/{index_name}", mapping, expected=(200, 201, 400))
    if result.get("error", {}).get("type") == "resource_already_exists_exception":
        print(f"索引 {index_name} 已存在，保留现有 Mapping")
    elif "error" in result:
        raise RuntimeError(result["error"])
    else:
        print(f"已创建索引 {index_name}")


def import_bulk(index_name, bulk_path, batch_documents=1000):
    imported = 0
    with bulk_path.open(encoding="utf-8") as file:
        while True:
            lines = []
            for _ in range(batch_documents * 2):
                line = file.readline()
                if not line:
                    break
                lines.append(line)
            if not lines:
                break
            payload = ("\n".join(line.rstrip("\n") for line in lines) + "\n").encode("utf-8")
            result = request("POST", "/_bulk?refresh=wait_for", payload, "application/x-ndjson")
            failures = [item["index"] for item in result.get("items", []) if item.get("index", {}).get("error")]
            if result.get("errors") or failures:
                raise RuntimeError(f"Bulk 导入失败，首个错误：{failures[0] if failures else result}")
            imported += len(lines) // 2
            print(f"{index_name}：已导入 {imported} 条")


def main():
    parser = argparse.ArgumentParser(description="生成 Bulk 文件并初始化微博热搜 Elasticsearch 演示")
    parser.add_argument("--convert-only", action="store_true", help="只生成 Bulk 文件，不连接 Elasticsearch")
    args = parser.parse_args()

    counts = {}
    for index_name, source in DATASETS.items():
        target = DATA_DIR / f"bulk_{'hot_search' if index_name == 'weibo_hot_search' else 'user_behavior'}.json"
        counts[index_name] = convert_to_bulk(source, index_name, target)
        print(f"已生成 {target.relative_to(ROOT)}（{counts[index_name]} 条）")
    if args.convert_only:
        return

    wait_for_es()
    for index_name in DATASETS:
        create_index(index_name)
        bulk_path = DATA_DIR / f"bulk_{'hot_search' if index_name == 'weibo_hot_search' else 'user_behavior'}.json"
        import_bulk(index_name, bulk_path)
        actual = request("GET", f"/{index_name}/_count")["count"]
        if actual != counts[index_name]:
            raise RuntimeError(f"{index_name} 数量校验失败：预期 {counts[index_name]}，实际 {actual}")
        print(f"{index_name} 数量校验通过：{actual} 条")


if __name__ == "__main__":
    main()
