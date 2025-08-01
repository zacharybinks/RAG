#!/bin/sh
# This script runs when the container starts.

# Create a new config.js file in the web root
echo "window.config = {" > /usr/share/nginx/html/config.js
# Read the REACT_APP_API_URL from the environment and write it to the file
echo "  API_URL: \"${REACT_APP_API_URL}\"" >> /usr/share/nginx/html/config.js
echo "};" >> /usr/share/nginx/html/config.js

# Start the Nginx server in the foreground
nginx -g 'daemon off;'