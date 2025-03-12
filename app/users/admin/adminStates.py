from aiogram.fsm.state import StatesGroup, State


# Create questions
class AddAdmin(StatesGroup):
    write_telegram_id = State()
    write_fullname = State()


class AddManager(StatesGroup):
    write_telegram_id = State()
    write_fullname = State()
    write_username = State()


class AdminEdit(StatesGroup):
    waiting_for_fullname = State()
    waiting_for_role = State()

class ManagerEdit(StatesGroup):
    waiting_for_fullname = State()
    waiting_for_role = State()
    waiting_for_username = State()


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


class ReportFilter(StatesGroup):
    waiting_for_period_input = State()


class BroadcastStates(StatesGroup):
    waiting_for_filter = State()
    waiting_for_media = State()
    waiting_for_text = State()
    confirmation = State()
    broadcast_history = State()


class PhotoIdGen(StatesGroup):
    waiting_for_zip = State()

class AddSupport(StatesGroup):
    write_telegram_id = State()
    write_fullname = State()
    write_phone = State()

class SupportEditFullname(StatesGroup):
    waiting_for_fullname = State()

class SupportEditPhone(StatesGroup):
    waiting_for_phone = State()

class SupportEditRole(StatesGroup):
    waiting_for_role = State()

class SupportEditTelegram(StatesGroup):
    waiting_for_telegram = State()
