from aiogram.fsm.state import StatesGroup, State


class ManagerEditProduct(StatesGroup):
    waiting_for_input = State()
