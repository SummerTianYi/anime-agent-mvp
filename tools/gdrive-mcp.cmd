@echo off
rem zcode: gdrive MCP launcher - Google API needs the local proxy on this machine
set HTTPS_PROXY=http://127.0.0.1:7897
set HTTP_PROXY=http://127.0.0.1:7897
set GDRIVE_OAUTH_PATH=D:\UserData\Administrator\Documents\Codex\2026-08-28\https-github-com-summertianyi-anime-agent\work\anime-agent-mvp\gcp-oauth.keys.json
set GDRIVE_CREDENTIALS_PATH=C:\Users\26052\.gmail-mcp\gdrive-credentials.json
npx -y @modelcontextprotocol/server-gdrive %*
