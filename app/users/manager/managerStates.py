from aiogram.fsm.state import StatesGroup, State


class ManagerEditProduct(StatesGroup):
    waiting_for_input = State()


class ManagerStates(StatesGroup):
    viewing_orders = State()
    viewing_order_detail = State()