"""
Система локализации приложения
Поддержка: Русский (RU) и Английский (EN)
"""

LOCALIZATION = {
    'en': {
        'window_title': 'Interactive Geometric Analysis and Function Visualization Studio',
        
        'toolbar_grid': 'Grid',
        'toolbar_language': 'Language',
        'toolbar_save': 'Save',
        'toolbar_load': 'Load',
        
        'tool_select': 'Select',
        'tool_point': 'Point',
        'tool_line': 'Line',
        'tool_circle': 'Circle',
        'tool_polygon': 'Polygon',
        'tool_angle': 'Angle',
        'tool_text': 'Text',
        
        'function_input': 'y = ',
        'function_add': 'Add',
        'function_delete': 'Delete',
        'function_functions': 'Functions',
        
        'dialog_angle_title': 'Enter Angle',
        'dialog_angle_prompt': 'Enter angle in degrees:',
        'dialog_text_title': 'Enter Text',
        'dialog_text_prompt': 'Enter text:',
        'dialog_save_title': 'Save Project',
        'dialog_save_prompt': 'File name:',
        'dialog_load_title': 'Load Project',
        'dialog_load_prompt': 'File name:',
        
        'msg_saved': '✓ Saved: ',
        'msg_loaded': '✓ Loaded: ',
        'msg_error': '✗ Error: ',
        'msg_error_save': '✗ Save error: ',
        'msg_error_load': '✗ Load error: ',
        'msg_file_not_found': '✗ File not found: ',
        'msg_initialized': '✓ DrawingCanvas initialized',
        'msg_tool_changed': '→ Tool: ',
        'msg_click': 'Click: ',
        'msg_function_error': '✗ Error adding function \'{}\': {}',
        
        'coord_x': 'x: ',
        'coord_y': ', y: ',
    },
    
    'ru': {
        'window_title': 'Студия интерактивного геометрического анализа и визуализации функций',
        
        'toolbar_grid': 'Сетка',
        'toolbar_language': 'Язык',
        'toolbar_save': 'Сохранить',
        'toolbar_load': 'Загрузить',
        
        'tool_select': 'Выбрать',
        'tool_point': 'Точка',
        'tool_line': 'Линия',
        'tool_circle': 'Круг',
        'tool_polygon': 'Многоугольник',
        'tool_angle': 'Угол',
        'tool_text': 'Текст',
        
        'function_input': 'y = ',
        'function_add': 'Добавить',
        'function_delete': 'Удалить',
        'function_functions': 'Функции',
        
        'dialog_angle_title': 'Ввод угла',
        'dialog_angle_prompt': 'Введите угол в градусах:',
        'dialog_text_title': 'Ввод текста',
        'dialog_text_prompt': 'Введите текст:',
        'dialog_save_title': 'Сохранить проект',
        'dialog_save_prompt': 'Имя файла:',
        'dialog_load_title': 'Загрузить проект',
        'dialog_load_prompt': 'Имя файла:',
        
        'msg_saved': '✓ Сохранено: ',
        'msg_loaded': '✓ Загружено: ',
        'msg_error': '✗ Ошибка: ',
        'msg_error_save': '✗ Ошибка сохранения: ',
        'msg_error_load': '✗ Ошибка загрузки: ',
        'msg_file_not_found': '✗ Файл не найден: ',
        'msg_initialized': '✓ DrawingCanvas инициализирован',
        'msg_tool_changed': '→ Инструмент: ',
        'msg_click': 'Клик: ',
        'msg_function_error': '✗ Ошибка при добавлении функции \'{}\': {}',
        
        'coord_x': 'x: ',
        'coord_y': ', y: ',
    }
}


class Localization:
    """Менеджер локализации"""
    
    def __init__(self, language='en'):
        self.current_language = language if language in LOCALIZATION else 'en'
        self.strings = LOCALIZATION[self.current_language]
    
    def get(self, key: str, default: str = '') -> str:
        """Получить переведенную строку"""
        return self.strings.get(key, default)
    
    def set_language(self, language: str):
        """Изменить язык"""
        if language in LOCALIZATION:
            self.current_language = language
            self.strings = LOCALIZATION[self.current_language]
            return True
        return False
    
    def get_current_language(self) -> str:
        """По��учить текущий язык"""
        return self.current_language
    
    def get_available_languages(self) -> list:
        """Получить доступные языки"""
        return list(LOCALIZATION.keys())


# Создаём глобальный объект локализации
i18n = Localization('en')