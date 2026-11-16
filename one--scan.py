import os
import platform
import subprocess
import wmi

# Инициализация WMI для доступа к системе
try:
    c = wmi.WMI()
except Exception as e:
    print(f"Ошибка инициализации WMI: {e}")
    print("Убедитесь, что скрипт запущен от имени администратора.")
    input("Нажмите Enter для выхода...")
    exit()

def get_system_info():
    """Собирает и выводит основную информацию о системе."""
    print("\n" + "="*50)
    print("ИНФОРМАЦИЯ О СИСТЕМЕ")
    print("="*50)

    # 1. ОС
    os_info = platform.uname()
    print(f"Компьютер:      {os_info.node}")
    print(f"ОС:             {os_info.system} {os_info.release} (версия {os_info.version})")
    print(f"Архитектура:    {os_info.machine}")

    # 2. Процессор (CPU)
    try:
        cpu = c.Win32_Processor()[0]
        print(f"Процессор:      {cpu.Name.strip()}")
        print(f"Ядра/Потоки:    {cpu.NumberOfCores} / {cpu.NumberOfLogicalProcessors}")
        print(f"Частота:        {cpu.MaxClockSpeed} MHz")
    except Exception:
        print("Процессор:      Не удалось получить данные")

    # 3. Оперативная память (RAM)
    try:
        mem_modules = c.Win32_PhysicalMemory()
        total_ram = sum(int(m.Capacity) for m in mem_modules) / (1024**3)
        print(f"ОЗУ (всего):    {total_ram:.2f} GB")
        # Вывод планок (если их несколько)
        for i, m in enumerate(mem_modules):
            speed = getattr(m, 'Speed', 'N/A')
            cap = int(m.Capacity) / (1024**3)
            print(f"  Планка {i+1}:     {cap:.1f} GB @ {speed} MHz")
    except Exception:
        print("ОЗУ:            Не удалось получить данные")

    # 4. Видеокарта (GPU)
    try:
        for gpu in c.Win32_VideoController():
            vram = int(gpu.AdapterRAM) / (1024**3) if gpu.AdapterRAM else 0
            print(f"Видеокарта:     {gpu.Name} ({vram:.1f} GB)")
    except Exception:
        print("Видеокарта:     Не удалось получить данные")

    # 5. Диски
    print("-" * 30)
    print("ДИСКИ:")
    try:
        for disk in c.Win32_DiskDrive():
            size = int(disk.Size) / (1024**3)
            print(f"  {disk.Model}: {size:.1f} GB (Интерфейс: {disk.InterfaceType})")
    except Exception:
        print("  Не удалось получить данные о дисках")

    # 6. Сеть (IP и MAC)
    print("-" * 30)
    print("СЕТЬ:")
    try:
        for nic in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
            print(f"  Адаптер: {nic.Description}")
            print(f"    MAC: {nic.MACAddress}")
            if nic.IPAddress:
                print(f"    IP:  {', '.join(nic.IPAddress)}")
    except Exception:
        print("  Не удалось получить данные о сети")

    print("="*50 + "\n")

def open_system_tool(choice):
    """Открывает системные утилиты по выбору."""
    commands = {
        "1": ("Диспетчер задач", "taskmgr"),
        "2": ("Редактор реестра", "regedit"),
        "3": ("Управление компьютером", "compmgmt.msc"),
        "4": ("Службы", "services.msc"),
        "5": ("Командная строка", "cmd"),
        "6": ("Панель управления", "control"),
        "7": ("Параметры Windows", "start ms-settings:"),
        "8": ("Монитор ресурсов", "resmon"),
        "9": ("Сведения о системе", "msinfo32"),
        "10": ("Управление дисками", "diskmgmt.msc"),
    }

    if choice in commands:
        name, cmd = commands[choice]
        print(f"Запуск: {name}...")
        try:
            # Для UWP приложений (Параметры) нужен start, для обычных exe - прямой запуск
            if cmd.startswith("start "):
                os.system(cmd)
            else:
                subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"Ошибка запуска: {e}")
    else:
        print("Неверный выбор.")

def main():
    while True:
        print("\n" + "="*50)
        print("ГЛАВНОЕ МЕНЮ")
        print("="*50)
        print("1. Показать информацию о ПК")
        print("2. Открыть системную утилиту")
        print("0. Выход")
        print("-" * 50)

        choice = input("Выберите действие: ")

        if choice == "1":
            get_system_info()
        elif choice == "2":
            print("\nДоступные утилиты:")
            print("1. Диспетчер задач")
            print("2. Редактор реестра")
            print("3. Управление компьютером")
            print("4. Службы")
            print("5. Командная строка")
            print("6. Панель управления")
            print("7. Параметры Windows")
            print("8. Монитор ресурсов")
            print("9. Сведения о системе")
            print("10. Управление дисками")
            tool_choice = input("Выберите номер утилиты (или 0 для отмены): ")
            if tool_choice != "0":
                open_system_tool(tool_choice)
        elif choice == "0":
            print("Выход...")
            break
        else:
            print("Неверный ввод. Попробуйте снова.")

if __name__ == "__main__":
    # Рекомендуется запускать от имени администратора для полного доступа к WMI
    main()