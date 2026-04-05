#!/usr/bin/env bash
# Get current date in YYYYMMDD format
export RELEASE_DATE=$(date +%Y%m%d)

# Run gh release create with dynamic date
gh release create "database-$RELEASE_DATE" \
  ../backend/random-2hu-stuff.db \
  full-data.csv \
  --title "database-$RELEASE_DATE" \
  --notes "database update for $RELEASE_DATE"
