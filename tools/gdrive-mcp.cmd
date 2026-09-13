@echo off
rem zcode entry; Codex: retain read-only handlers, fix expired-token refresh.
setlocal
if not defined HTTPS_PROXY set HTTPS_PROXY=http://127.0.0.1:7897
if not defined HTTP_PROXY set HTTP_PROXY=http://127.0.0.1:7897
if not defined GDRIVE_OAUTH_PATH set "GDRIVE_OAUTH_PATH=%~dp0..\gcp-oauth.keys.json"
if not defined GDRIVE_CREDENTIALS_PATH set "GDRIVE_CREDENTIALS_PATH=%USERPROFILE%\.gmail-mcp\gdrive-credentials.json"
node "%~dp0gdrive\index.mjs" %*
exit /b %errorlevel%
