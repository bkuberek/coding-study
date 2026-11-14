#!/bin/sh
# commands.run: builds the app with no network, then runs it in this script's place.
set -e
go build -o build/server .
exec build/server
