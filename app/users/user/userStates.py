from aiogram.fsm.state import StatesGroup, State


# Create questions
class ChangeFullname(StatesGroup):
    write_fullname = State()


class ChangePhone(StatesGroup):
    write_phone = State()


class ChangeAddress(StatesGroup):
    write_address = State()


class CartOrder(StatesGroup):
    customizing = State()


class OrderInfo(StatesGroup):
    waiting_fullname = State()
    waiting_phone = State()
    waiting_address = State()

class UserData(StatesGroup):
    waiting_fullname = State()
    waiting_phone = State()
    waiting_address = State()