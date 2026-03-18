# Hook para PyInstaller: incluye todos los submódulos de tkcalendar.
# Necesario en Python 3.12+ donde --collect-all puede fallar por SyntaxWarning
# en tkcalendar/calendar_.py ("\ " escape sequence).

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata

hiddenimports = collect_submodules("tkcalendar") + [
    "tkcalendar",
    "tkcalendar.calendar_",
    "tkcalendar.dateentry",
    "tkcalendar.tooltip",
]

datas = collect_data_files("tkcalendar")

# tkcalendar usa babel para localización de fechas
hiddenimports += collect_submodules("babel") + [
    "babel.dates",
    "babel.numbers",
    "babel.core",
]

datas += collect_data_files("babel")

try:
    datas += copy_metadata("tkcalendar")
    datas += copy_metadata("babel")
except Exception:
    pass
