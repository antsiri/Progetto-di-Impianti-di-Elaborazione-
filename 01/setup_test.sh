#!/bin/bash

# --- CONFIGURATION ---
TARGET_DIR="./files"        # Local folder or server path
CSV_FILE="file.csv"         # File for JMeter
NUM_FILES_EXTRA=15          # File to generate

mkdir -p "$TARGET_DIR"      # Create the folder if not exists
rm -rf "$TARGET_DIR"/*

echo "filepath" > "$CSV_FILE"

create_file() {
    local size_str=$1
    local bytes=$2
    local filename="file_${size_str}.dat"
    local filepath="${TARGET_DIR}/${filename}"

    if command -v fallocate &> /dev/null; then
        fallocate -l "$bytes" "$filepath" 2>/dev/null || dd if=/dev/urandom of="$filepath" bs=1 count="$bytes" status=none
    else 
        dd if=/dev/urandom of="$filepath" bs=1 count="$bytes" status=none
    fi

    echo "/files/${filename}" >> "$CSV_FILE"
    echo " [+] Created: ${filename} (${bytes} bytes)"
}

echo "=== 1. File generation ==="
create_file "1KB" 1024
create_file "100KB" 102400
create_file "1MB" 1048576
create_file "50MB" 52428800
create_file "100MB" 104857600

echo -e "\n=== 2. Random file generation ($NUM_FILES_EXTRA files) ==="
for i in $(seq 1 $NUM_FILES_EXTRA); do 
    RAND_KB=$(( (RANDOM % 15000) + 50 ))        # Between 50KB to 15MB
    BYTES=$(( RAND_KB * 1024 ))
    create_file "extra_${i}_${RAND_KB}KB" $BYTES
done

echo -e "\n=== Completed! ==="
echo "File saved in: $TARGET_DIR"
echo "CSV generated: $CSV_FILE (Total rows: $(wc -l < $CSV_FILE))"