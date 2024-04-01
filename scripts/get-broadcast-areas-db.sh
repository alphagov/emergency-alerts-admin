#!/usr/bin/env sh

TARGET_LOCAL_DIR=$1
SOURCE_BUCKET_DIR=$2
QUIET_DOWNLOAD=$3

if ! [ -f "$TARGET_LOCAL_DIR/broadcast-areas.sqlite3" ]; then
	if aws s3 ls "s3://$SOURCE_BUCKET_DIR/broadcast-areas.sqlite3"; then
		echo "Downloading Broadcast Areas Sqlite file..."
		if [ -n "$QUIET_DOWNLOAD" ]; then
			aws s3 cp "s3://$SOURCE_BUCKET_DIR/broadcast-areas.sqlite3" "$TARGET_LOCAL_DIR" --quiet
		else \
			aws s3 cp "s3://$SOURCE_BUCKET_DIR/broadcast-areas.sqlite3" "$TARGET_LOCAL_DIR"
		fi
	else \
		echo "Broadcast Areas Sqlite file required by application not found in S3 bucket. Exiting...";
		exit 1;
	fi
else
	echo "Broadcast Areas Sqlite file already exists";
fi
