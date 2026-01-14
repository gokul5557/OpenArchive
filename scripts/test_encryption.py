import asyncio
import encryption
import storage
import time
import os

def main():
    print("--- Encryption Test ---")
    
    # 1. Unit Test
    data = b"Hello World - Secret"
    enc = encryption.encrypt_data(data)
    print(f"Encrypted ({len(enc)} bytes): {enc[:10]}...")
    
    assert enc != data
    
    dec = encryption.decrypt_data(enc)
    assert dec == data
    print("Unit Test Passed.")
    
    # 2. Storage Integration
    obj_name = f"test_enc_{int(time.time())}.txt"
    print(f"Uploading {obj_name}...")
    
    # Upload via Storage Wrapper (Should Encrypt)
    storage.upload_blob(obj_name, data)
    
    # Verify Raw in MinIO (Simulate Attacker)
    # Use boto3 directly to bypass auto-decrypt
    raw_response = storage.s3_client.get_object(Bucket=storage.BUCKET_NAME, Key=obj_name)
    raw_content = raw_response['Body'].read()
    
    print(f"Raw Content from MinIO: {raw_content[:15]}...")
    
    if raw_content == data:
        print("FAILURE: Data is stored in PLAINTEXT!")
    else:
        print("SUCCESS: Data is stored ENCRYPTED.")
        
    # Verify Decryption
    print("Downloading via Storage Wrapper...")
    retrieved = storage.get_blob(obj_name)
    
    if retrieved == data:
        print("SUCCESS: Transparent Decryption works.")
    else:
        print(f"FAILURE: Decryption returned wrong data: {retrieved}")

if __name__ == "__main__":
    main()
