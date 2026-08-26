"""
 * author Antonio Sirignano
 * created on 18-08-2026-16h-41m
 * github: https://github.com/antsiri
 * copyright 2026
"""

import os
import random
import csv

RESOURCE_TIERS = {
    "low":       [(13.5, "KB"), (20, "KB"), (23.4, "KB"), (98, "KB"), (99.7, "KB")],
    "mid_low":   [(137, "KB"), (139, "KB"), (184, "KB"), (458, "KB"), (514, "KB")],
    "mid":       [(716, "KB"), (0.98, "MB"), (0.99, "MB"), (1, "MB"), (1.3, "MB")],
    "mid_high":  [(2, "MB"), (2.13, "MB"), (2.14, "MB"), (5.07, "MB"), (5.19, "MB")],
    "high":      [(9.21, "MB"), (9.38, "MB"), (9.58, "MB"), (10.1, "MB")],
}

def size_to_bytes(value, unit):
    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024**2,
    }

    clean_unit = unit.strip().upper()
    if clean_unit not in units:
        raise ValueError(f"Unit '{unit}' not avaible!")

    return int(value * units[clean_unit])

def generate_sample(path, size_bytes, chunk_size: int = 1024 * 1024) -> None:
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    bytes_written = 0

    with open(path, "wb") as f:
        while bytes_written < size_bytes:
            to_write = min(chunk_size, size_bytes - bytes_written)

            f.write(os.urandom(to_write))

            bytes_written += to_write
    

def main(output_dir="server/static", manifest_path="server/static/manifest.csv"):
    os.makedirs(output_dir, exist_ok=True)
    rows = []
    for tier, files in RESOURCE_TIERS.items():
        for value, unit in files:
            filename = f"Sample_{value}{unit}.bin"
            path = os.path.join(output_dir, filename)
            size_bytes = size_to_bytes(value, unit)
            generate_sample(path, size_to_bytes(value, unit))
            rows.append({'filename': filename, 'tier': tier, 'size_bytes': size_bytes})

    with open(manifest_path, 'w', newline="") as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'tier', 'size_bytes'])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()

