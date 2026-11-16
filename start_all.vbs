' start_all.vbs
Set WshShell = CreateObject("WScript.Shell")

' Запускаем сервер скрыто
WshShell.Run "cmd /c cd /d C:\Users\1\Desktop\my-notes && python server.py", 0, False

' Небольшая пауза, чтобы сервер успел стартовать (1 секунда)
WScript.Sleep 1000

' Запускаем агент скрыто
WshShell.Run "cmd /c cd /d C:\Users\1\Desktop\my-notes && python agent.py connect ws://localhost:8000/ws/agent", 0, False