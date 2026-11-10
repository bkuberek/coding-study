#!/bin/sh
# commands.run: builds the app offline, then runs it in this script's place, so the build's memory
# is free before the app starts and the app is the container's own process.
set -e
gradle --offline --quiet installDist
exec build/install/app/bin/app
