@echo off

cd %~dp0

where python
if %errorlevel% NEQ 0 (
    echo Can not find python.
    goto FAILED
)

python _juci.py %*

:SUCCEEDED
echo *SUCCEEDED*
goto EOF

:FAILED
echo *FAILED*
goto EOF

:EOF
