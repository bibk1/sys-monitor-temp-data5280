# platforms/telegram/states/systemd.py
from aiogram.fsm.state import State, StatesGroup

class SystemdStates(StatesGroup):
    viewing_logs = State()
    # Редактирование файлов пока не предусмотрено