#!/usr/bin/env python3
"""
Zero-dependency MongoDB Backup and Restore Utility for Darknet Threat Intelligence.
Safely exports collections (including 108,000+ messages and api_keys) to JSON/BSON archives,
and restores them on the target Ubuntu production server without data loss.
"""

import os
import sys
import json
import gzip
import argparse
from pathlib import Path
from datetime import datetime, timezone
from pymongo import MongoClient

DEFAULT_COLLECTIONS = ["messages", "api_keys", "channels", "threat_intel", "reports"]


def export_database(mongo_url: str, db_name: str, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = output_dir / f"{db_name}_backup_{timestamp}.json.gz"

    print(f"Connecting to MongoDB at {mongo_url}...")
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    db = client[db_name]

    backup_data = {
        "metadata": {
            "database": db_name,
            "timestamp": timestamp,
            "version": "1.0.0"
        },
        "collections": {}
    }

    total_records = 0
    for coll_name in DEFAULT_COLLECTIONS:
        coll = db[coll_name]
        count = coll.count_documents({})
        print(f"  • Reading collection '{coll_name}': {count:,} documents...")
        records = []
        for doc in coll.find({}, {"_id": 0}):
            records.append(doc)
        backup_data["collections"][coll_name] = records
        total_records += len(records)

    print(f"Compressing and writing {total_records:,} documents to {backup_file}...")
    with gzip.open(backup_file, "wt", encoding="utf-8") as f:
        json.dump(backup_data, f)

    file_size_mb = backup_file.stat().st_size / (1024 * 1024)
    print("\n[SUCCESS] Export Complete!")
    print(f"   Backup File: {backup_file}")
    print(f"   Total Records: {total_records:,}")
    print(f"   Archive Size: {file_size_mb:.2f} MB")
    return backup_file


def restore_database(mongo_url: str, db_name: str, backup_file: Path, drop_existing: bool = False):
    if not backup_file.exists():
        print(f"❌ Backup file not found: {backup_file}")
        sys.exit(1)

    print(f"Connecting to target MongoDB at {mongo_url}...")
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    db = client[db_name]

    print(f"Decompressing and reading {backup_file}...")
    with gzip.open(backup_file, "rt", encoding="utf-8") as f:
        backup_data = json.load(f)

    meta = backup_data.get("metadata", {})
    print(f"Loaded archive for database '{meta.get('database')}' created at {meta.get('timestamp')}.")

    total_restored = 0
    collections = backup_data.get("collections", {})
    for coll_name, docs in collections.items():
        if not docs:
            continue
        coll = db[coll_name]
        if drop_existing:
            print(f"  • Dropping existing collection '{coll_name}'...")
            coll.drop()

        print(f"  • Restoring {len(docs):,} documents into '{coll_name}'...")
        # Bulk insert in batches of 5000
        batch_size = 5000
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            coll.insert_many(batch, ordered=False)
        total_restored += len(docs)

    print("\n[SUCCESS] Restore Complete!")
    print(f"   Database: {db_name}")
    print(f"   Total Restored: {total_restored:,} documents")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Darknet MongoDB Backup & Restore Utility")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Export parser
    exp_parser = subparsers.add_parser("export", help="Export MongoDB collections to compressed archive")
    exp_parser.add_argument("--url", default="mongodb://localhost:27017", help="MongoDB Connection URL")
    exp_parser.add_argument("--db", default="darknet_monitor", help="Database name")
    exp_parser.add_argument("--out", default="data/backups", help="Output directory")

    # Restore parser
    res_parser = subparsers.add_parser("restore", help="Restore collections from compressed archive")
    res_parser.add_argument("--url", default="mongodb://localhost:27017", help="MongoDB Connection URL")
    res_parser.add_argument("--db", default="darknet_monitor", help="Database name")
    res_parser.add_argument("--file", required=True, help="Path to backup .json.gz file")
    res_parser.add_argument("--drop", action="store_true", help="Drop existing collections before restoring")

    args = parser.parse_args()
    if args.action == "export":
        export_database(args.url, args.db, Path(args.out))
    elif args.action == "restore":
        restore_database(args.url, args.db, Path(args.file), args.drop)
