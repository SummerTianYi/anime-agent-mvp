@echo off
rem zcode: gmail MCP launcher - Google API needs the local proxy on this machine
set HTTPS_PROXY=http://127.0.0.1:7897
set HTTP_PROXY=http://127.0.0.1:7897
npx -y @gongrzhe/server-gmail-autoauth-mcp %*
