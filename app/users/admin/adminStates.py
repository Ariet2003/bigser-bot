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

class ManagerEdit(StatesGroup):
    waiting_for_fullname = State()
    waiting_for_role = State()


class DeleteEmployeeStates(StatesGroup):
    waiting_for_confirmation = State()


class CategoryEdit(StatesGroup):
    waiting_for_new_name = State()


class CategoryAdd(StatesGroup):
    waiting_for_category_name = State()


class SubcategoryEdit(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_parent_category = State()


class SubcategoryAdd(StatesGroup):
    waiting_for_name = State()
    waiting_for_parent_category = State()


class ProductEdit(StatesGroup):
    waiting_for_excel_file = State()