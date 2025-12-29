# bot/states.py
from aiogram.fsm.state import State, StatesGroup

class AddWallet(StatesGroup):
    waiting_for_input = State()

class AddToken(StatesGroup):
    waiting_for_input = State()