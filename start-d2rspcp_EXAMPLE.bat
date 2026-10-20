@echo off
cd /d C:\D2RSPCP
start "" venv\Scripts\pythonw.exe d2rspcp.py client --server http://YOUSERVERIP:8420 --token YOURTOKEN --saves "%USERPROFILE%\Saved Games\Diablo II Resurrected" --config config --interval 5
exit