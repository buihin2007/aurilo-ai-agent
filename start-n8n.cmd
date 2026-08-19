@echo off
REM Launches n8n for the Aurilo closing-variance pilot.
REM Run this via Task Scheduler at log on ("Run only when user is logged on"),
REM so n8n uses this user's profile: workflows and credentials live in
REM %USERPROFILE%\.n8n, and the NODES_EXCLUDE / N8N_RESTRICT_FILE_ACCESS_TO /
REM GENERIC_TIMEZONE variables are set per user by SETUP.md step 3.
cd /d C:\aurilo-ai-agent
n8n start
