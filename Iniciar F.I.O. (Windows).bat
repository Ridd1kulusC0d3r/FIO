@echo off
chcp 65001 >nul
title F.I.O. Lab
cd /d "%~dp0"
echo.
echo  F.I.O. Lab - abrindo a bancada no seu navegador...
echo  (esta janela precisa ficar aberta enquanto voce usa o programa)
echo.
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
if errorlevel 1 (
  echo  [!] Python 3.10 ou mais novo nao foi encontrado.
  echo      Instale em https://www.python.org/downloads/ e marque a opcao
  echo      "Add python.exe to PATH" durante a instalacao. Depois abra este
  echo      arquivo de novo.
  echo.
  pause
  exit /b 1
)
%PY% -m fio demo
%PY% -m fio lab bancada
pause
