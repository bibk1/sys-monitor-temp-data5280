# platforms/telegram/states/docker.py
from aiogram.fsm.state import State, StatesGroup

class DockerStates(StatesGroup):
    viewing_logs = State()
    editing_compose = State()