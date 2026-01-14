import email
import email.policy
import base64
import sys

def test_parsing(file_path):
    print(f"Reading {file_path}...")
    with open(file_path, 'r') as f:
        content = f.read()

    print("Parsing EML...")
    try:
        msg_obj = email.message_from_string(content, policy=email.policy.default)
        body_text = ""
        body_html = ""
        attachments = []
        inline_images = {}

        for part in msg_obj.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition", ""))
            cid = part.get("Content-ID", "").strip("<>")
            
            print(f"Processing Part: {ctype}, Multipart? {part.is_multipart()}")

            # Simulate logic
            payload = None
            if not part.is_multipart():
                try:
                    payload = part.get_content()
                    print(f"  Got content: {len(payload) if payload else 0} chars/bytes")
                except Exception as e:
                    print(f"  Failed to get content: {e}")
                    payload = part.get_payload(decode=True)

            is_attachment = "attachment" in cdispo or (cid and not ctype.startswith("text"))
            
            if is_attachment:
                 print("  -> Is Attachment")
            else:
                 print("  -> Body Part")

        print("Parsing SUCCESS")

    except Exception as e:
        print(f"Parsing FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parsing("/home/gokul/archier/OpenArchive/a.txt")
