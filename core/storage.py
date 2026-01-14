import boto3
import os
from botocore.exceptions import ClientError

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "password")
BUCKET_NAME = "archive-blobs"

s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

def ensure_bucket():
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except ClientError:
        s3_client.create_bucket(Bucket=BUCKET_NAME)

import encryption

def upload_blob(object_name, data):
    ensure_bucket()
    try:
        # Encrypt before upload
        encrypted = encryption.encrypt_data(data)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=object_name,
            Body=encrypted
        )
        return True
    except Exception as e:
        print(f"Error uploading blob: {e}")
        return False

def get_blob(object_name):
    ensure_bucket()
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=object_name)
        raw_data = response['Body'].read()
        
        # Try Decrypt
        decrypted = encryption.decrypt_data(raw_data)
        if decrypted is not None:
            return decrypted
        
        # Fallback for legacy plaintext (optional, for transition)
        return raw_data
        
    except Exception as e:
        print(f"Error getting blob: {e}")
        return None

def delete_blob(object_name):
    ensure_bucket()
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_name)
        return True
    except Exception as e:
        print(f"Error deleting blob: {e}")
        return False

def blob_exists(object_name):
    ensure_bucket()
    try:
        s3_client.head_object(Bucket=BUCKET_NAME, Key=object_name)
        return True
    except ClientError:
        return False
