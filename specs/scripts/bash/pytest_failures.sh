#!/usr/bin/env bash

# Run pytest and capture output
output=$(pytest --no-cov 2>&1)
exit_code=$?

# Extract from FAILURES line through short test summary info line
failures=$(pytest --no-cov --tb=long | awk '/^=+ FAILURES =+$/,/^=+ short test summary info =+$/')

if [ -n "$failures" ]; then
    echo "$failures"
else
    echo "No failures found"
fi

exit $exit_code
