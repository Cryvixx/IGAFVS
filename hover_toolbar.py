from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor
import re

# Импортируем локализацию
from localization import Localization

# Глобальный объект локализации (будет установлен из main_window)
i18n = None

def set_i18n(localization):
    """Установить глобальный объект локализации"""
    global i18n
    i18n = localization
    print(f"DEBUG: set_i18n called, i18n is now {i18n}")


class FunctionInput(QWidget):
    """Виджет для ввода функций"""
    function_added = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Текстовая метка
        self.label = QLabel(i18n.get('function_input'))
        self.label.setStyleSheet("color: #505050; font-size: 14px;")
        layout.addWidget(self.label)

        # Поле для ввода
        self.input = QLineEdit()
        self.input.setPlaceholderText("sin(x), cos(x), sqrt(x), 1/x, x^2, 2, pi...")
        self.input.setMinimumWidth(200)
        self.input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #a0a0a0;
            }
        """)
        layout.addWidget(self.input)

        # Кнопка добавления
        self.add_btn = QPushButton(i18n.get('function_add'))
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8e8e8;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        self.add_btn.clicked.connect(self.add_function)
        layout.addWidget(self.add_btn)

        layout.addStretch()

    def add_function(self):
        """Добавить функцию"""
        function_text = self.input.text().strip()
        if function_text:
            if self.validate_function(function_text):
                self.function_added.emit(function_text)
                self.input.clear()
            else:
                print(f"{i18n.get('msg_error')}Некорректная функция")

    def validate_function(self, func):
        """Проверить корректность функции"""
        if func.count('(') != func.count(')'):
            return False
        if 'x' not in func and not any(c.isdigit() for c in func):
            return False
        return True

    def update_language(self):
        """Обновить текст элементов при смене языка"""
        self.label.setText(i18n.get('function_input'))
        self.add_btn.setText(i18n.get('function_add'))


class FunctionListWidget(QWidget):
    """Виджет со списком добавленных функций"""
    function_toggled = pyqtSignal(int, bool)
    function_deleted = pyqtSignal(int)
    
    COLORS = [
        QColor(40, 200, 40),
        QColor(255, 0, 0),
        QColor(0, 100, 255),
        QColor(255, 165, 0),
        QColor(160, 32, 240),
        QColor(220, 20, 60),
        QColor(0, 206, 209),
        QColor(184, 134, 11),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.functions = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Заголовок
        self.title = QLabel(i18n.get('function_functions'))
        self.title.setStyleSheet("color: #505050; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.title)
        
        # Список
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #f5f5f5;
            }
        """)
        self.list_widget.setMaximumHeight(100)
        layout.addWidget(self.list_widget)

    def add_function(self, func_text, index):
        """Добавить функцию в список"""
        color = self.COLORS[index % len(self.COLORS)]
        
        item = QListWidgetItem()
        item.setSizeHint(QSize(200, 35))
        
        item_widget = self._create_function_item(func_text, index, color)
        
        item.setData(Qt.UserRole, index)
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, item_widget)
        
        self.functions.append({
            'text': func_text,
            'visible': True,
            'index': index,
            'color': color
        })

    def _create_function_item(self, func_text, index, color):
        """Создать виджет для одного элемента ��писка"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # Цветной квадратик
        color_label = QLabel()
        color_label.setFixedSize(15, 15)
        color_label.setStyleSheet(f"background-color: {color.name()}; border-radius: 2px;")
        layout.addWidget(color_label)
        
        # Текст функции
        text_label = QLabel(f"y = {func_text}")
        text_label.setStyleSheet("color: #505050; font-size: 10px;")
        layout.addWidget(text_label)
        
        # Кнопка показа/скрытия
        toggle_btn = QPushButton("✓")
        toggle_btn.setFixedSize(25, 20)
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(True)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8e8e8;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:checked {
                background-color: #90EE90;
                border: 1px solid #4CAF50;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        toggle_btn.clicked.connect(lambda checked: self.function_toggled.emit(index, checked))
        layout.addWidget(toggle_btn)
        
        # Кнопка удаления
        delete_btn = QPushButton("✕")
        delete_btn.setFixedSize(25, 20)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e8e8e8;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #ffcccc;
                border: 1px solid #ff0000;
            }
        """)
        delete_btn.clicked.connect(lambda: self.function_deleted.emit(index))
        layout.addWidget(delete_btn)
        
        return widget

    def remove_function(self, index):
        """Удалить функцию из списка"""
        for i, func in enumerate(self.functions):
            if func['index'] == index:
                self.list_widget.takeItem(i)
                self.functions.pop(i)
                break

    def update_language(self):
        """Обновить текст элементов при смене языка"""
        self.title.setText(i18n.get('function_functions'))


class HoverToolbar(QWidget):
    """Главная панель инструментов"""
    
    grid_toggled = pyqtSignal(bool)
    function_added = pyqtSignal(str)
    function_deleted = pyqtSignal(int)
    function_toggled = pyqtSignal(int, bool)
    tool_selected = pyqtSignal(str)
    save_requested = pyqtSignal()
    load_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setMaximumHeight(200)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
            }
        """)
        
        self.tool_buttons = {}
        self.tool_labels = {}
        self.grid_btn = None
        self.grid_label = None
        self.save_btn = None
        self.save_label = None
        self.load_btn = None
        self.load_label = None
        
        self.function_input = None
        self.function_list = None
        
        self.init_ui()
        self.show()

    def init_ui(self):
        """Инициализировать интерфейс"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(15, 5, 15, 5)

        # Слой кнопок инструментов
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Список инструментов
        tools = [
            ("select", i18n.get('tool_select')),
            ("point", i18n.get('tool_point')),
            ("line", i18n.get('tool_line')),
            ("circle", i18n.get('tool_circle')),
            ("polygon", i18n.get('tool_polygon')),
            ("angle", i18n.get('tool_angle')),
            ("text", i18n.get('tool_text')),
        ]

        # Создаём кнопки инструментов
        for btn_name, btn_label in tools:
            container = QWidget()
            vlay = QVBoxLayout(container)
            vlay.setSpacing(2)
            vlay.setContentsMargins(0, 0, 0, 0)

            btn = QPushButton()
            btn.setObjectName(btn_name)
            btn.setIcon(QIcon(f"icons/{btn_name}.png"))
            btn.setIconSize(QSize(24, 24))
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e8e8e8;
                    border-radius: 5px;
                    padding: 4px;
                    border: 1px solid #d0d0d0;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border: 1px solid #c0c0c0;
                }
                QPushButton:checked {
                    background-color: #ffffff;
                    border: 2px solid #a0a0a0;
                }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(self.on_tool_selected)

            label = QLabel(btn_label)
            label.setAlignment(Qt.AlignCenter)
            label.setFont(QFont("Arial", 8))
            label.setStyleSheet("color: #505050;")

            vlay.addWidget(btn)
            vlay.addWidget(label)
            buttons_layout.addWidget(container)
            
            self.tool_buttons[btn_name] = btn
            self.tool_labels[btn_name] = label

        # Кнопка GRID
        grid_container = self._create_tool_button("grid", i18n.get('toolbar_grid'))
        self.grid_btn = grid_container['btn']
        self.grid_label = grid_container['label']
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(True)
        self.grid_btn.clicked.connect(self.on_grid_toggled)
        buttons_layout.addWidget(grid_container['container'])

        # Кнопка SAVE
        save_container = self._create_tool_button("save", i18n.get('toolbar_save'))
        self.save_btn = save_container['btn']
        self.save_label = save_container['label']
        self.save_btn.clicked.connect(self.on_save)
        buttons_layout.addWidget(save_container['container'])

        # Кнопка LOAD
        load_container = self._create_tool_button("load", i18n.get('toolbar_load'))
        self.load_btn = load_container['btn']
        self.load_label = load_container['label']
        self.load_btn.clicked.connect(self.on_load)
        buttons_layout.addWidget(load_container['container'])
        
        buttons_layout.addStretch()

        # Виджеты функций
        self.function_input = FunctionInput()
        self.function_input.function_added.connect(self.on_function_added)

        self.function_list = FunctionListWidget()
        self.function_list.function_toggled.connect(self.on_function_toggled)
        self.function_list.function_deleted.connect(self.on_function_deleted)

        main_layout.addLayout(buttons_layout)
        main_layout.addWidget(self.function_input)
        main_layout.addWidget(self.function_list)

    def _create_tool_button(self, tool_name, label_text):
        """Создать контейнер с кнопкой и подписью"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)
        
        btn = QPushButton()
        btn.setObjectName(tool_name)
        btn.setIcon(QIcon(f"icons/{tool_name}.png"))
        btn.setIconSize(QSize(24, 24))
        btn.setFixedSize(40, 40)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #e8e8e8;
                border-radius: 5px;
                padding: 4px;
                border: 1px solid #d0d0d0;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border: 1px solid #c0c0c0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:checked {
                background-color: #ffffff;
                border: 2px solid #a0a0a0;
            }
        """)
        layout.addWidget(btn)
        
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 8))
        label.setStyleSheet("color: #505050;")
        layout.addWidget(label)
        
        return {
            'container': container,
            'btn': btn,
            'label': label
        }

    def on_tool_selected(self):
        """Обработчик выбора инструмента"""
        sender = self.sender()
        if sender:
            for btn in self.tool_buttons.values():
                if btn != sender:
                    btn.setChecked(False)
            
            tool_name = sender.objectName()
            print(f"{i18n.get('msg_tool_changed')}{tool_name}")
            self.tool_selected.emit(tool_name)

    def on_grid_toggled(self):
        """Обработчик переключения сетки"""
        self.grid_toggled.emit(self.grid_btn.isChecked())

    def on_function_added(self, function_text):
        """Обработчик добавления функции"""
        func_index = len(self.function_list.functions)
        self.function_list.add_function(function_text, func_index)
        self.function_added.emit(function_text)

    def on_function_deleted(self, index):
        """Обработчик удаления функции"""
        self.function_deleted.emit(index)
        self.function_list.remove_function(index)

    def on_function_toggled(self, index, visible):
        """Обработчик переключения видимости функции"""
        self.function_toggled.emit(index, visible)

    def on_save(self):
        """Обработчик кнопки сохранения"""
        self.save_requested.emit()

    def on_load(self):
        """Обработчик кнопки загрузки"""
        self.load_requested.emit()

    def update_language(self):
        """Обновить язык всех элементов панели"""
        print(f"\nDEBUG: update_language() called")
        print(f"DEBUG: Current language: {i18n.get_current_language()}")
        
        # Обновляем инструменты
        tools_dict = {
            'select': i18n.get('tool_select'),
            'point': i18n.get('tool_point'),
            'line': i18n.get('tool_line'),
            'circle': i18n.get('tool_circle'),
            'polygon': i18n.get('tool_polygon'),
            'angle': i18n.get('tool_angle'),
            'text': i18n.get('tool_text'),
        }
        
        for btn_name, label in self.tool_labels.items():
            new_text = tools_dict.get(btn_name, btn_name)
            label.setText(new_text)
            print(f"DEBUG: Tool '{btn_name}': {new_text}")
        
        # Обновляем кнопки действий
        self.grid_label.setText(i18n.get('toolbar_grid'))
        print(f"DEBUG: Grid: {i18n.get('toolbar_grid')}")
        
        self.save_label.setText(i18n.get('toolbar_save'))
        print(f"DEBUG: Save: {i18n.get('toolbar_save')}")
        
        self.load_label.setText(i18n.get('toolbar_load'))
        print(f"DEBUG: Load: {i18n.get('toolbar_load')}")
        
        # Обновляем виджеты функций
        self.function_input.update_language()
        self.function_list.update_language()
        
        print(f"DEBUG: update_language() completed\n")

    def closeEvent(self, event):
        """Закрытие панели"""
        try:
            for btn in self.tool_buttons.values():
                if btn.clicked.receivers() > 0:
                    btn.clicked.disconnect()
        except:
            pass
        event.accept()