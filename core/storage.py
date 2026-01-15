import boto3
import os
import secrets
from datetime import datetime
import asyncio
from botocore.exceptions import ClientError

try:
    from config import settings
    import encryption
    import database
    import integrity
except ImportError:
    from core.config import settings
    from core import encryption, database, integrity

import aiofiles
MINIO_ENDPOINT = settings.MINIO_ENDPOINT
MINIO_ACCESS_KEY = settings.MINIO_ROOT_USER
MINIO_SECRET_KEY = settings.MINIO_ROOT_PASSWORD
BUCKET_NAME = settings.MINIO_BUCKET_NAME

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
        # encrypted = encryption.encrypt_data(data)
        # DISABLE SSE due to double-encryption issues
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=object_name,
            Body=data
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
