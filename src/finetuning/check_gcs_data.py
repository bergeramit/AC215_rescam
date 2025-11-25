"""
Check what data exists in GCS buckets for fine-tuning
"""
import os
from google.cloud import storage

PROJECT_ID = "1097076476714"

def list_bucket_contents(bucket_name, prefix=""):
    """List all files in a GCS bucket with given prefix"""
    try:
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
        
        files = []
        for blob in blobs:
            if not blob.name.endswith("/"):  # Skip directories
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "updated": blob.updated
                })
        return files
    except Exception as e:
        print(f"Error accessing bucket {bucket_name}: {e}")
        return []

def main():
    print("=" * 70)
    print("Checking GCS Buckets for Training Data")
    print("=" * 70)
    
    buckets_to_check = [
        ("rescam-dataset-bucket", ["raw-datasets/", "processed-dataset/", "user_emails/"]),
        ("rescam-rag-bucket", ["vertex_ai_index_data/", "metadata/"]),
        ("rescam-user-emails", ["user-classifications/", "temp-emails/"]),
    ]
    
    total_files = 0
    total_size = 0
    
    for bucket_name, prefixes in buckets_to_check:
        print(f"\n📦 Bucket: {bucket_name}")
        print("-" * 70)
        
        for prefix in prefixes:
            files = list_bucket_contents(bucket_name, prefix)
            if files:
                print(f"\n  📁 {prefix}")
                for f in files[:10]:  # Show first 10 files
                    size_mb = f["size"] / (1024 * 1024)
                    print(f"    - {f['name']} ({size_mb:.2f} MB, updated: {f['updated']})")
                if len(files) > 10:
                    print(f"    ... and {len(files) - 10} more files")
                total_files += len(files)
                total_size += sum(f["size"] for f in files)
            else:
                print(f"\n  📁 {prefix} - (empty)")
    
    print("\n" + "=" * 70)
    print(f"Summary: {total_files} files, {total_size / (1024*1024):.2f} MB total")
    print("=" * 70)
    
    # Check for labeled training data
    print("\n🔍 Looking for labeled training data...")
    
    # Check processed-dataset for parquet files
    processed_files = list_bucket_contents("rescam-dataset-bucket", "processed-dataset/")
    parquet_files = [f for f in processed_files if f["name"].endswith(".parquet")]
    
    if parquet_files:
        print(f"✅ Found {len(parquet_files)} parquet file(s) in processed-dataset/")
        print("   These likely contain labeled emails (label 0/1)")
        for f in parquet_files:
            print(f"   - {f['name']} ({f['size'] / (1024*1024):.2f} MB)")
    else:
        print("❌ No parquet files found in processed-dataset/")
    
    # Check user_emails for CSV files
    user_email_files = list_bucket_contents("rescam-dataset-bucket", "user_emails/")
    csv_files = [f for f in user_email_files if f["name"].endswith(".csv")]
    
    if csv_files:
        print(f"\n✅ Found {len(csv_files)} CSV file(s) in user_emails/")
        for f in csv_files:
            print(f"   - {f['name']} ({f['size'] / (1024*1024):.2f} MB)")
    else:
        print("\n❌ No CSV files found in user_emails/")

if __name__ == "__main__":
    main()

