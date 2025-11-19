"""
Check the cleaned dataset to see how many labeled examples we have for fine-tuning
"""
import pandas as pd
from google.cloud import storage
import os
import tempfile

PROJECT_ID = "1097076476714"
BUCKET_NAME = "rescam-dataset-bucket"
FILE_PATH = "processed-dataset/cleaned_dataset.parquet"

def download_and_analyze():
    """Download parquet file and analyze it"""
    print("=" * 70)
    print("Analyzing Training Data in GCS")
    print("=" * 70)
    
    # Download file
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(FILE_PATH)
    
    print(f"\n📥 Downloading {FILE_PATH}...")
    with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as tmp_file:
        blob.download_to_filename(tmp_file.name)
        print(f"✅ Downloaded to temporary file")
        
        # Load and analyze
        print(f"\n📊 Loading parquet file...")
        df = pd.read_parquet(tmp_file.name)
        
        print(f"\n{'='*70}")
        print("Dataset Summary")
        print(f"{'='*70}")
        print(f"Total emails: {len(df):,}")
        print(f"Columns: {list(df.columns)}")
        
        # Check labels
        if 'label' in df.columns:
            print(f"\n📋 Label Distribution:")
            label_counts = df['label'].value_counts()
            for label, count in label_counts.items():
                label_name = "Phishing" if label == 1 else "Legitimate"
                print(f"  {label_name} (label={label}): {count:,} emails ({count/len(df)*100:.1f}%)")
        
        # Check for other useful columns
        print(f"\n📝 Available Fields:")
        for col in df.columns:
            if col != 'label':
                non_null = df[col].notna().sum()
                print(f"  - {col}: {non_null:,} non-null values")
        
        # Sample data
        print(f"\n📧 Sample Emails:")
        print("-" * 70)
        for idx, row in df.head(3).iterrows():
            label_name = "🚨 PHISHING" if row.get('label') == 1 else "✅ LEGITIMATE"
            print(f"\n{label_name}")
            print(f"  Subject: {str(row.get('subject', 'N/A'))[:60]}")
            print(f"  Sender: {str(row.get('sender', 'N/A'))[:50]}")
            print(f"  Body preview: {str(row.get('body', 'N/A'))[:100]}...")
        
        # Check if we have enough for fine-tuning
        print(f"\n{'='*70}")
        print("Fine-Tuning Readiness")
        print(f"{'='*70}")
        
        if 'label' in df.columns:
            min_class = df['label'].value_counts().min()
            total = len(df)
            
            print(f"Total labeled examples: {total:,}")
            print(f"Smallest class size: {min_class:,}")
            
            if total >= 1000:
                print("✅ SUFFICIENT for fine-tuning (1000+ examples)")
            elif total >= 200:
                print("⚠️  MINIMAL for fine-tuning (200-999 examples)")
                print("   Will work but results may be limited")
            else:
                print("❌ INSUFFICIENT for fine-tuning (<200 examples)")
                print("   Need to generate more data")
        
        # Clean up
        os.unlink(tmp_file.name)
        
        print(f"\n{'='*70}")

if __name__ == "__main__":
    try:
        download_and_analyze()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. GCP credentials set up (gcloud auth application-default login)")
        print("2. Access to the bucket")
        print("3. pandas and pyarrow installed")

