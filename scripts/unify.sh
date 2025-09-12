#!/bin/bash

INPUT_DIR="$1"
OUT_DIR="${INPUT_DIR%/}_unified"

# Copy the directory
cp -R "$INPUT_DIR" "$OUT_DIR"

# Process each subdirectory
for SUBDIR in "$OUT_DIR"/*/; do
    [ -d "$SUBDIR" ] || continue
    NAME=$(basename "$SUBDIR")
    echo "Processing $NAME..."
    START=$(date +%s)
    unified-cli --overwrite "$SUBDIR"
    END=$(date +%s)
    echo "Time for $NAME: $((END - START))s"
done
