import json
from collections import Counter
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "docs" / "charts"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def load_data(path):
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * atan2(sqrt(a), sqrt(1 - a))


def filter_by_distance(data, center_lat, center_lon, max_distance_km):
    results = []
    for source in data:
        item = source.copy()
        location = item["location"]
        item["distance_km"] = round(haversine_distance(center_lat, center_lon, location["lat"], location["lon"]), 2)
        if item["distance_km"] <= max_distance_km:
            results.append(item)
    return sorted(results, key=lambda item: item["distance_km"])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hot_search = load_data(DATA_DIR / "weibo_hot_search.json")
    behavior = load_data(DATA_DIR / "user_behavior.json")
    hot_locations = Counter(item["location_name"] for item in hot_search)
    behavior_locations = Counter(item["location_name"] for item in behavior)
    cities = sorted(set(hot_locations) & set(behavior_locations))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].bar(cities, [hot_locations[city] for city in cities], color="#FF6B6B")
    axes[0].set_title("热搜发布地点分布")
    axes[0].tick_params(axis="x", rotation=45)
    axes[1].bar(cities, [behavior_locations[city] for city in cities], color="#4ECDC4")
    axes[1].set_title("用户行为地点分布")
    axes[1].tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "geo_distribution.png", dpi=150)
    plt.close()

    nearby = filter_by_distance(hot_search, 39.9042, 116.4074, 500)
    print(f"已分析 {len(hot_search)} 条热搜和 {len(behavior)} 条行为数据；北京 500 km 内命中 {len(nearby)} 条")


if __name__ == "__main__":
    main()
