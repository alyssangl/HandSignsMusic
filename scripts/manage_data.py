"""
manage_data.py
See and clean up your recorded data.

Run from the HandSignsMusic folder:

  List all bursts (grouped by sign):
      python scripts/manage_data.py list

  List bursts for one sign only:
      python scripts/manage_data.py list --sign 5

  Delete one burst (from the CSV AND its images):
      python scripts/manage_data.py delete guy_1790842209992

Tip: the burst id is also in the image file names, e.g.
     guy_guy_1790842209992_001.jpg  ->  burst id = guy_1790842209992
"""

import argparse
import csv
from collections import OrderedDict
from pathlib import Path

import config

CSV_PATH = Path(config.DATA_DIR) / "landmarks.csv"
IMG_DIR = Path(config.DATA_DIR) / "images"


def read_rows():
    if not CSV_PATH.exists():
        raise SystemExit(f"No data file found at {CSV_PATH}")
    with open(CSV_PATH, newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def cmd_list(sign=None):
    header, body = read_rows()
    bursts = OrderedDict()      # burst_id -> [person, label, count]
    for r in body:
        person, label, burst_id = r[0], r[1], r[2]
        if burst_id not in bursts:
            bursts[burst_id] = [person, label, 0]
        bursts[burst_id][2] += 1

    signs = [sign] if sign else config.SIGNS
    for s in signs:
        items = [(b, p, c) for b, (p, l, c) in bursts.items() if l == s]
        total = sum(c for _, _, c in items)
        name = config.SIGN_NAMES.get(s, s)
        print(f"\nSign {s} ({name}) - {len(items)} bursts, {total} samples")
        for i, (b, p, c) in enumerate(items, 1):
            print(f"  {i:>2}. {b:<28} person: {p:<10} samples: {c}")


def cmd_delete(burst_id):
    header, body = read_rows()
    keep = [r for r in body if r[2] != burst_id]
    removed = len(body) - len(keep)
    if removed == 0:
        print(f"No burst found with id '{burst_id}'. Use 'list' to see the ids.")
        return

    label = next(r[1] for r in body if r[2] == burst_id)
    answer = input(f"Delete burst '{burst_id}' (sign {label}, {removed} samples)? [y/n] ")
    if answer.strip().lower() != "y":
        print("Cancelled.")
        return

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(keep)

    images = list(IMG_DIR.glob(f"*/*{burst_id}_*.jpg"))
    for p in images:
        p.unlink()
    print(f"Deleted {removed} samples from the CSV and {len(images)} images.")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list", help="show bursts")
    p_list.add_argument("--sign", help="only show this sign, e.g. 5 or rest")
    p_del = sub.add_parser("delete", help="delete one burst")
    p_del.add_argument("burst_id")
    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args.sign)
    else:
        cmd_delete(args.burst_id)


if __name__ == "__main__":
    main()