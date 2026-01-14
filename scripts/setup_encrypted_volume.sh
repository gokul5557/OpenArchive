#!/bin/bash
# setup_encrypted_volume.sh
# Purpose: Create an encrypted loopback file to store sensitive search index data.
# Usage: sudo ./setup_encrypted_volume.sh

VOLUME_NAME="openarchive_secure"
IMG_FILE="openarchive_data.img"
MOUNT_POINT="./secure_data"
SIZE_MB=512 # Reduced to 512MB for speed

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

echo "--- OpenArchive Secure Storage Setup ---"

# 1. Create Image File (if not exists)
if [ ! -f "$IMG_FILE" ]; then
    echo "[1/5] Creating ${SIZE_MB}MB image file..."
    # Try fallocate (instant), fallback to dd
    if command -v fallocate >/dev/null; then
        fallocate -l ${SIZE_MB}M $IMG_FILE
    else
        dd if=/dev/zero of=$IMG_FILE bs=1M count=$SIZE_MB status=progress
    fi
else
    echo "[1/5] Image file exists. Skipping creation."
fi

# 2. Format with LUKS (Encryption)
# Check if already LUKS
if ! cryptsetup isLuks $IMG_FILE; then
    echo "[2/5] Encrypting volume..."
    if [ -z "$PASSPHRASE" ]; then
        echo "ERROR: PASSPHRASE env var not set."
        exit 1
    fi
    # --batch-mode prevents "Are you sure?" prompt hang
    echo -n "$PASSPHRASE" | cryptsetup luksFormat --batch-mode $IMG_FILE -
else
    echo "[2/5] Volume already encrypted."
fi

# 3. Open the Volume
echo "[3/5] Opening encrypted volume..."
if [ ! -e "/dev/mapper/$VOLUME_NAME" ]; then
    echo -n "$PASSPHRASE" | cryptsetup open $IMG_FILE $VOLUME_NAME -
else
    echo "Volume already open."
fi

# 4. Format Filesystem (EXT4) - Only first time!
# We check if it has a filesystem
if ! blkid /dev/mapper/$VOLUME_NAME | grep -q "ext4"; then
    echo "[4/5] Formatting filesystem (First time setup)..."
    mkfs.ext4 /dev/mapper/$VOLUME_NAME
else
    echo "[4/5] Filesystem already exists."
fi

# 5. Mount
mkdir -p $MOUNT_POINT
mount /dev/mapper/$VOLUME_NAME $MOUNT_POINT
echo "[5/5] Mounted at $MOUNT_POINT"

echo "Success! Point your Docker volumes to $(realpath $MOUNT_POINT)"
echo "To Unmount: sudo umount $MOUNT_POINT && sudo cryptsetup close $VOLUME_NAME"
