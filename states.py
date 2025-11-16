from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    # Состояния для начала смены (сохраняем существующий функционал)
    shift_action = State()
    waiting_round = State()  # состояние для записи кружка
    
    # Состояния для передачи ТМЦ
    transfer_tmc_photo = State()
    
    # Состояния для обхода
    patrol_photos = State()
    
    # Состояния для осмотра
    inspection_photos = State()
    
    # Состояния для проблем
    problem_description = State()
    problem_photo = State()
    
    # Состояния для экстренных вызовов
    emergency_type = State()
    emergency_description = State()
    
    # Состояния для проверки поста
    post_check_location = State()
    post_check_video = State()

class AdminStates(StatesGroup):
    awaiting_group_shortname = State()