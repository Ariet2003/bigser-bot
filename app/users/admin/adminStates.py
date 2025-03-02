from aiogram.fsm.state import StatesGroup, State


# Create questions
class AddAdmin(StatesGroup):
    write_telegram_id = State()
    write_fullname = State()


class AddManager(StatesGroup):
    write_telegram_id = State()
    write_fullname = State()


class AdminEdit(StatesGroup):
    waiting_for_fullname = State()
    waiting_for_role = State()