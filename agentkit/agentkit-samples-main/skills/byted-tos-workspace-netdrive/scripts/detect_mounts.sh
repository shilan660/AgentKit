#!/bin/bash

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

MOUNT_ROOT="/root/.openclaw/workspace"

# Check if root directory exists
if [ ! -d "$MOUNT_ROOT" ]; then
    echo "No workspace mount root found at $MOUNT_ROOT"
    echo "Please configure a network drive (configure TOS bucket information) via the arkClaw interface menu bar."
    exit 0
fi

# Detect mounts using df and grep as requested
# We use grep to filter lines containing the mount root
mounts=$(df -P | grep "$MOUNT_ROOT")

if [ -z "$mounts" ]; then
    echo "No network drives mounted in workspace."
    echo "Please configure a network drive (configure TOS bucket information) via the arkClaw interface menu bar."
    exit 0
fi

echo "Detected network drives (Buckets):"
echo "$mounts" | while read -r line; do
    # Extract the mount point path. 
    # df -P ensures POSIX output (no line wrapping), mount point is the last field.
    mount_point=$(echo "$line" | awk '{print $NF}')
    
    # Verify it is indeed under our root (double check)
    if [[ "$mount_point" == "$MOUNT_ROOT"* ]]; then
        # Extract bucket name (last component of path)
        bucket_name=$(basename "$mount_point")
        echo "Bucket: $bucket_name (Path: $mount_point)"
    fi
done
