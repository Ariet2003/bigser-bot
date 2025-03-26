from aiogram.fsm.state import StatesGroup, State


# Create questions
class UserRegister(StatesGroup):
    write_fullname = State()
    write_phone_number = State()
