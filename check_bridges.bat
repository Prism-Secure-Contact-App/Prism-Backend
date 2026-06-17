@echo off
REM Direct SSH command to check bridge status
REM Using ssh client directly via command line

setlocal enabledelayedexpansion

echo Connecting to server...

ssh -o ConnectTimeout=30 -o StrictHostKeyChecking=no fathertkt@100.125.63.77 ^
  "cd /home/fathertkt/prism-backend && docker compose ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'prism-whatsapp|prism-meta|NAMES'"

if %errorlevel% equ 0 (
    echo.
    echo ✅ Command succeeded!
) else (
    echo.
    echo ⚠️ Error during SSH connection
)
