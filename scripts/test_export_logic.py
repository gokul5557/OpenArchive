
import sys
import os

# Add project root and core to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'core'))

# Mock storage
import storage
def mock_get_blob(name):
    print(f"Mock fetching blob: {name}")
    if "1234567890" in name:
        return b"This is the re-hydrated attachment content"
    return None

storage.get_blob = mock_get_blob

from exports import generate_eml

# Sample stripped EML
stripped_eml = """MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="boundary"

--boundary
Content-Type: text/plain

Hello World

--boundary
Content-Type: text/plain; name="test.txt"
Content-Disposition: attachment; filename="test.txt"
X-OpenArchive-CAS-Ref: 1234567890

[CAS_REF:1234567890]

--boundary--
"""

print("Testing generate_eml...")
msg = generate_eml({}, stripped_eml)

print("Walking message parts:")
for part in msg.walk():
    ctype = part.get_content_type()
    filename = part.get_filename()
    print(f"- Content-Type: {ctype}")
    
    if filename:
        payload = part.get_payload(decode=True)
        print(f"  Filename: {filename}")
        print(f"  Payload Size: {len(payload)}")
        if payload == b"This is the re-hydrated attachment content":
            print("  SUCCESS: Attachment re-hydrated correctly!")
        else:
            print(f"  FAIL: Attachment content mismatch. Got: {payload}")

    if "X-OpenArchive-CAS-Ref" in part:
        print("  FAIL: CAS Header still present")
    elif filename:
        print("  Check: X-OpenArchive-CAS-Ref removed as expected.")
