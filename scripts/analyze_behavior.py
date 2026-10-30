import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "user_behavior.json"
OUTPUT_DIR = ROOT / "docs" / "charts"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def load_data(path):
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def save_chart(name):
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / name, dpi=150)
    plt.close()


def analyze(data):
    results = {}
    action_counts = Counter(item["action_type"] for item in data)
    results["action_type"] = dict(action_counts)
    plt.figure(figsize=(8, 5))
    plt.bar(action_counts.keys(), action_counts.values(), color="#4ECDC4")
    plt.title("用户行为类型分布")
    save_chart("action_type_distribution.png")

    device_counts = Counter(item["device_type"] for item in data)
    results["device_type"] = dict(device_counts)
    plt.figure(figsize=(7, 6))
    plt.pie(device_counts.values(), labels=device_counts.keys(), autopct="%1.1f%%")
    plt.title("用户设备类型分布")
    save_chart("device_distribution.png")

    dwell = [item["dwell_time"] for item in data if item["dwell_time"] > 0]
    results["dwell_time"] = {"mean": float(np.mean(dwell)), "median": float(np.median(dwell)), "max": max(dwell), "min": min(dwell)}
    plt.figure(figsize=(9, 5))
    plt.hist(dwell, bins=50, color="#45B7D1")
    plt.title("用户停留时间分布")
    save_chart("dwell_time_distribution.png")

    keywords = Counter(item["search_keyword"] for item in data if item["action_type"] == "search")
    results["top_keywords"] = keywords.most_common(15)
    plt.figure(figsize=(10, 7))
    labels = [item[0][:12] for item in results["top_keywords"]][::-1]
    values = [item[1] for item in results["top_keywords"]][::-1]
    plt.barh(labels, values, color="#FF6B6B")
    plt.title("用户搜索关键词 Top 15")
    save_chart("top_search_keywords.png")

    hours = Counter(datetime.strptime(item["timestamp"], "%Y-%m-%dT%H:%M:%S").hour for item in data)
    results["hourly"] = dict(sorted(hours.items()))
    plt.figure(figsize=(10, 5))
    plt.plot(list(hours.keys()), list(hours.values()), marker="o")
    plt.xticks(range(24))
    plt.title("用户行为时间分布")
    save_chart("hourly_pattern.png")
    return results


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data(DATA_PATH)
    results = analyze(data)
    report_path = OUTPUT_DIR / "user_behavior_report.json"
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已分析 {len(data)} 条行为数据，结果保存至 {report_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
