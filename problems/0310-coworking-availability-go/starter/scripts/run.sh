#!/bin/sh
# commands.run: builds the app with no network, then runs it in this script's place, so the build's
# memory is free before the app starts and the app is the container's own process.
set -e
go build -o build/server .
exec build/server
