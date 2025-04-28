from aiogram.fsm.state import StatesGroup, State

class UploadStates(StatesGroup):
    waiting_for_caption = State()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
