#!/usr/bin/env bash

echo "arg0: $0 arg1: $1 arg2: $2 arg3: $3 arg4: $4 arg5: $5"
echo "--- content of $1 start ---"
cat $1
echo "--- content of $1 end ---"

echo "{TOKEN} $(< $1)" >> '{TARGET_FILE}'
