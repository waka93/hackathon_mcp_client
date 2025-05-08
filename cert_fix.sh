#!/bin/bash

# Define the directory to search in
search_dir="/app"

# Define the file to search for
file_to_search="sse.py"

# Run the find command and store the results
file_paths=$(find $search_dir -type f -path "*/mcp/client/$file_to_search" 2>/dev/null)

# Check if any files were found
if [ -n "$file_paths" ]; then
    echo "Files found:"
    echo "$file_paths"
    
    # Loop through each file path and update the string
    for file_path in $file_paths; do
        sed -i 's/httpx\.AsyncClient(headers=headers)/httpx.AsyncClient(headers=headers, verify=False)/g' "$file_path"
        echo "Updated: $file_path"
    done
else
    echo "No files found."
fi