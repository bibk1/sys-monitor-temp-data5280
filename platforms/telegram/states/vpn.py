# platforms/telegram/states/vpn.py
from aiogram.fsm.state import State, StatesGroup

class VPNStates(StatesGroup):
    waiting_for_sources = State()
    waiting_for_config = State()
    waiting_for_russian_cidrs = State()