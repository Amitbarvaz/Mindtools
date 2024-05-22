#!/bin/bash

# Ensure the script exits if any command fails
set -e

# Source nvm script to ensure nvm is available in this session
export NVM_DIR="$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "${HOME}/.nvm" || printf %s "${XDG_CONFIG_HOME}/nvm")"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Use the specified Node.js version
nvm use

# Install Bower
npm install bower

# Install Bower dependencies
bower install

# Install jsPlumb library in a specific location
npm install --prefix ./staticfiles/lib/ jsplumb@1.7.9

# Move the jsPlumb library to the desired location
mv ./staticfiles/lib/node_modules/jsplumb/ ./staticfiles/lib/jsplumb/

# Remove unnecessary files
rm ./staticfiles/lib/package.json ./staticfiles/lib/package-lock.json ./staticfiles/lib/node_modules/.package-lock.json

# Remove the now empty node_modules directory
rmdir ./staticfiles/lib/node_modules/
