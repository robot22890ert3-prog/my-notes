import subprocess
import re
from datetime import datetime, timedelta

def get_failed_logins(hours=24):
    """Показывает неудачные попытки входа в Windows за последние N часов."""
    since = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    
    # PowerShell-команда: берём события ID 4625 (неудачный вход)
    ps_command = (
        f"Get-WinEvent -FilterHashtable @{{LogName='Security'; "
        f"ID=4625; StartTime='{since}'}} -ErrorAction SilentlyContinue | "
        f"Select-Object TimeCreated, @{{Name='User';Expression={{$_.Properties[5].Value}}}}, "
        f"@{{Name='Source';Expression={{$_.Properties[19].Value}}}} | "
        f"ConvertTo-Csv -NoTypeInformation"
    )
    
    result = subprocess.run(
        ["powershell", "-Command", ps_command],
        capture_output=True, text=True, encoding="cp866"
    )
    
    lines = result.stdout.strip().splitlines()
    if len(lines) <= 1:
        print(f"За последние {hours} ч. неудачных входов не найдено.")
        return
    
    print(f"Неудачные попытки входа за последние {hours} ч.:\n")
    print(f"{'Время':<22} {'Пользователь':<20} {'Источник'}")
    print("-" * 70)
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) >= 3:
            time = parts[0].strip('"')
            user = parts[1].strip('"') or "—"
            source = parts[2].strip('"') or "—"
            print(f"{time:<22} {user:<20} {source}")

if __name__ == "__main__":
    # Требуются права администратора для чтения журнала Security
    get_failed_logins(hours=24)