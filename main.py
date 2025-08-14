import sys
import json
import os
import re
import shutil
from datetime import datetime
from glob import glob

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QScrollArea,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QHBoxLayout, QCheckBox, QTextEdit, QSplitter,
    QStyle, QMenu, QDialog, QFileDialog, QDialogButtonBox,
    QRadioButton, QMessageBox, QSpinBox, QInputDialog, QComboBox,
    QFontComboBox, QButtonGroup, QColorDialog, QTabWidget, QStatusBar,
    QToolButton, QAbstractItemView, QFrame, QPlainTextEdit, QAbstractSpinBox,
    QTreeWidget, QTreeWidgetItem, QSlider, QStackedWidget, QStyleOption, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QPoint, QRectF, QUrl, QPropertyAnimation, QEasingCurve, pyqtSignal, QByteArray,
    QSize, QTimer, QEvent, QParallelAnimationGroup, QObject
)
from PyQt6.QtGui import (
    QAction, QMouseEvent, QPainter, QPixmap, QColor, QFont, QIcon, QTextCursor,
    QScreen, QKeySequence, QShortcut, QLinearGradient, QPolygonF, QPalette, QFontDatabase,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtSvg import QSvgRenderer

# --- Файлы и константы ---
SETTINGS_FILE = "settings.json"
DATA_FILE = "data.json"
BACKUP_DIR = "backups" # <-- НОВЫЙ КАТАЛОГ ДЛЯ БЭКАПОВ

DEFAULT_SETTINGS = {
    "language": "ru_RU",
    "theme": "light",
    "trigger_pos": "right",
    "accent_color": "#00aa88",
    "notes_tree_enabled": True,
    "audio_folder": "",

    "light_theme_bg": "#f8f9fa",
    "light_theme_text": "#212529",
    "light_theme_list_text": "#212529",
    "dark_theme_bg": "#2b2b2b",
    "dark_theme_text": "#e6e6e6",
    "dark_theme_list_text": "#bbbbbb",

    "zen_bg_path": "",
    "zen_light_theme_bg": "#F5F5DC",
    "zen_dark_theme_bg": "#1c1c1c",
    "zen_editor_opacity": 85,
    "zen_padding_horiz": 20,
    "zen_padding_vert": 5,
    "zen_font_family": "Candara",
    "zen_font_size": 16,
    "zen_font_color": "",
    "zen_alignment": "left",
    "zen_first_line_indent": 20,

    "window_splitter_sizes": [250, 500, 350],

    "window_geometry": "",
    "window_left_visible": True,
    "window_right_visible": True,
    "window_editor_font_size": 0,
    "window_min_width_left": 260,
    "window_min_width_right": 380,

    "editor_padding_top": 8, # <-- НОВЫЕ НАСТРОЙКИ
    "editor_padding_bottom": 8,
    "editor_padding_left": 10,
    "editor_padding_right": 10,

    "autosave_interval_sec": 10,
    "task_templates": ["Позвонить ...", "Купить ...", "Написать ...", "Сделать ..."],
}

POMODORO_WORK_TIME = 25 * 60
POMODORO_BREAK_TIME = 5 * 60

# --- Утилиты ---

def theme_colors(settings: dict):
    """Возвращает набор цветов в зависимости от выбранной темы."""
    theme = settings.get("theme", "light")
    accent = settings.get("accent_color", "#007bff")
    if theme == "dark":
        bg = settings.get("dark_theme_bg", "#1e1e1e")
        text = settings.get("dark_theme_text", "#e6e6e6")
        list_text = settings.get("dark_theme_list_text", "#bbbbbb")
        is_dark = True
    else:
        bg = settings.get("light_theme_bg", "#ffffff")
        text = settings.get("light_theme_text", "#212529")
        list_text = settings.get("light_theme_list_text", "#212529")
        is_dark = False
    return is_dark, accent, bg, text, list_text

# --- Вспомогательные классы UI ---

class ThemedLineEdit(QLineEdit):
    """Поле ввода, которое создает стилизованное контекстное меню."""
    def __init__(self, main_parent=None, parent=None):
        super().__init__(parent)
        self.main_parent = main_parent

    def contextMenuEvent(self, event):
        standard_menu = self.createStandardContextMenu()
        
        if self.main_parent and hasattr(self.main_parent, '_create_themed_menu'):
            themed_menu = self.main_parent._create_themed_menu()
            themed_menu.addActions(standard_menu.actions())
            themed_menu.exec(event.globalPos())
        else:
            standard_menu.exec(event.globalPos())
            
class ThemedInputDialog(QDialog):
    """Диалоговое окно для ввода текста, стилизованное под тему приложения."""
    def __init__(self, parent, title, label, text="", settings=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(350)
        
        self.layout = QVBoxLayout(self)
        self.info_label = QLabel(label)
        self.input_field = QLineEdit(text)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        
        self.layout.addWidget(self.info_label)
        self.layout.addWidget(self.input_field)
        self.layout.addWidget(self.buttons)
        
        if settings:
            self.apply_theme(settings)

    def apply_theme(self, settings):
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        
        stylesheet = f"""
            QDialog {{ background-color: {bg}; }}
            QLabel {{ color: {text}; background-color: transparent; padding-bottom: 5px; }}
            QLineEdit {{
                background-color: {comp_bg}; border: 1px solid {border};
                border-radius: 4px; color: {text}; padding: 5px;
            }}
            QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {QColor(comp_bg).lighter(110).name()};
                border: 1px solid {accent};
            }}
        """
        self.setStyleSheet(stylesheet)

    def get_text(self):
        return self.input_field.text()
        
# --- Локализация ---
class LocalizationManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self, default_lang='ru_RU'):
        super().__init__()
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        self.locales_dir = os.path.join(base_path, "locales")
        self.translations = {}
        self._ensure_locales_exist()
        self.available_languages = self._scan_languages()
        self.current_lang = default_lang
        self.set_language(self.current_lang)

    def _ensure_locales_exist(self):
        if not os.path.isdir(self.locales_dir):
            os.makedirs(self.locales_dir)
        
        ru_path = os.path.join(self.locales_dir, 'ru_RU.json')
        if not os.path.exists(ru_path):
            ru_data = {
                "app_title": "Ассистент 2.0",
                "lang_name": "Русский", "add_task_button": "Добавить", "new_task_placeholder": "Новая задача...",
                "hide_completed_checkbox": "Скрыть выполненные", "delete_note_tooltip": "Удалить заметку", "delete_task_tooltip": "Удалить задачу",
                "notes_editor_label": "Редактор заметок:", "save_button": "Сохранить", "new_note_button": "Новая",
                "zen_button": "Zen", "search_placeholder": "Поиск по тексту...", "all_tags_combo": "Все теги",
                "new_note_placeholder": "Начните писать...", "unsaved_changes_status": "Несохраненные изменения...", "data_saved_status": "Данные сохранены",
                "word_count_label": "Слов", "pomodoro_label": "Pomodoro:", "pomodoro_start_btn": "Старт",
                "pomodoro_pause_btn": "Пауза", "pomodoro_reset_btn": "Сброс", "about_menu": "О программе...",
                "export_menu": "Экспорт заметок в Markdown...", "restore_menu": "Восстановить из резервной копии...", "exit_menu": "Выход",
                "add_list_menu": "Добавить список...", "rename_list_menu": "Переименовать список...", "delete_list_menu": "Удалить список...",
                "new_list_prompt": "Введите имя нового списка:", "rename_list_prompt": "Введите новое имя для списка:",
                "delete_list_confirm": "Вы уверены, что хотите удалить список '{list_name}'?", "settings_title": "Настройки",
                "settings_tab_general": "Общие", "settings_tab_appearance": "Оформление", "settings_tab_zen": "Редактор Zen",
                "settings_lang_label": "Язык:", "settings_theme_label": "Основная тема:", "settings_light_theme": "Светлая",
                "settings_dark_theme": "Тёмная", "settings_trigger_pos_label": "Позиция кнопки:", "settings_trigger_left": "Слева",
                "settings_trigger_right": "Справа", "settings_accent_color_label": "Акцентный цвет:", "settings_choose_color_btn": "Выбрать цвет...",
                "settings_light_theme_bg_label": "Фон светлой темы:", "settings_light_theme_text_label": "Текст светлой темы:",
                "settings_dark_theme_bg_label": "Фон тёмной темы:", "settings_dark_theme_text_label": "Текст тёмной темы:",
                "settings_light_theme_list_text_label": "Текст списков (светлая):", "settings_dark_theme_list_text_label": "Текст списков (тёмная):",
                "settings_zen_bg_label": "Фон Zen (картинка):", "settings_browse_btn": "Обзор...", "settings_clear_btn": "Очистить",
                "settings_transparent_editor": "Прозрачный редактор", "settings_font_label": "Шрифт", "settings_size_label": "Размер:",
                "settings_font_color_label": "Цвет шрифта:", "settings_alignment_label": "Выравнивание:", "settings_align_left": "По левому краю",
                "settings_align_justify": "По ширине", "settings_padding_horiz": "Гор. отступ (%):", "settings_padding_vert": "Верт. отступ (%):",
                "settings_first_line_indent": "Отступ 1-й строки (px):", "task_menu_edit": "Редактировать...",
                "task_menu_toggle_completed": "Отметить/Снять отметку", "note_pin_menu": "Закрепить", "note_unpin_menu": "Открепить",
                "list_management_tooltip": "Клик правой кнопкой для управления списками", "open_window_menu": "Открыть оконный режим…",
                "open_window_tooltip": "Открыть в оконном режиме", "left_column_toggle": "Список", "left_column_tooltip": "Показать/скрыть список заметок",
                "right_column_toggle": "Задачи", "right_column_tooltip": "Показать/скрыть список задач", "to_panel_button": "⇦ Панель",
                "to_panel_tooltip": "Открыть боковую панель", "tags_label": "Теги:", "to_task_btn": "➕ в задачи",
                "to_task_tooltip": "Добавить выделенный текст в задачи", "import_settings": "Импорт настроек…", "export_settings": "Экспорт настроек…",
                "task_templates_title": "Шаблоны задач", "task_templates_hint": "Один шаблон — одна строка:", "settings_enable_tree": "Древовидные заметки (beta)",
                "tree_new_folder": "Новая папка...", "tree_rename_folder": "Переименовать папку...",
                "tree_delete_folder": "Удалить папку", "tree_delete_note": "Удалить заметку", "tree_new_note_here": "Новая заметка здесь",
                "tree_confirm_delete_folder": "Удалить папку '{name}' со всем содержимым?", "settings_audio_folder_label": "Папка музыки:",
                "audio_toggle_tooltip": "Музыка", "audio_prev": "Предыдущий", "audio_next": "Следующий", "audio_play": "Воспроизвести",
                "audio_pause": "Пауза", "audio_stop": "Стоп", "audio_volume": "Громкость", "settings_zen_audio_folder_label": "Музыка Zen:",
                "new_note_title": "Новая заметка", "folder_description": "Описание папки", "note_editing": "Редактирование заметки",
                "settings_zen_light_theme_bg_label": "Фон Zen (светлая тема):",
                "settings_zen_dark_theme_bg_label": "Фон Zen (тёмная тема):",
                "settings_min_width_left": "Мин. ширина левой колонки:",
                "settings_min_width_right": "Мин. ширина правой колонки:",
                "task_filter_all": "Все",
                "task_filter_active": "Активные",
                "task_filter_completed": "Выполненные",
                "settings_min_width_left": "Мин. ширина левой колонки:", 
                "settings_min_width_right": "Мин. ширина правой колонки:", 
                "settings_padding_top": "Отступ сверху (px):",
                "settings_padding_bottom": "Отступ снизу (px):",
                "settings_padding_left": "Отступ слева (px):",
                "settings_padding_right": "Отступ справа (px):",
                "backup_manager_title": "Менеджер резервных копий",
                "backup_available_copies": "Доступные копии:",
                "backup_restore_btn": "Восстановить",
                "backup_delete_btn": "Удалить",
                "backup_no_copies": "Резервные копии не найдены.",
                "backup_confirm_restore": "Вы уверены, что хотите восстановить данные из копии от {date}?",
                "backup_confirm_delete": "Вы уверены, что хотите удалить эту резервную копию?",
                "settings_min_width_left": "Мин. ширина левой колонки:",
                "settings_min_width_right": "Мин. ширина правой колонки:",
                "settings_padding_top": "Отступ сверху (px):",
                "settings_padding_bottom": "Отступ снизу (px):",
                "settings_padding_left": "Отступ слева (px):",
                "settings_padding_right": "Отступ справа (px):",
                "settings_create_backup_now": "Создать бэкап сейчас",
                "zen_button_tooltip": "Перейти в режим Zen (полноэкранный редактор)",
                "window_button_tooltip": "Перейти в оконный режим",
                "backup_confirm_delete": "Вы уверены, что хотите удалить эту резервную копию?",
            }
            with open(ru_path, 'w', encoding='utf-8') as f:
                json.dump(ru_data, f, ensure_ascii=False, indent=2)

        en_path = os.path.join(self.locales_dir, 'en_US.json')
        if not os.path.exists(en_path):
            en_data = {
                "app_title": "Assistant 2.0",
                "lang_name": "English", "add_task_button": "Add", "new_task_placeholder": "New task...", "hide_completed_checkbox": "Hide completed",
                "delete_note_tooltip": "Delete note", "delete_task_tooltip": "Delete task", "notes_editor_label": "Notes Editor:", "save_button": "Save",
                "new_note_button": "New", "zen_button": "Zen", "search_placeholder": "Search...", "all_tags_combo": "All tags",
                "new_note_placeholder": "Start writing...", "unsaved_changes_status": "Unsaved changes...", "data_saved_status": "Data saved",
                "word_count_label": "Words", "pomodoro_label": "Pomodoro:", "pomodoro_start_btn": "Start", "pomodoro_pause_btn": "Pause",
                "pomodoro_reset_btn": "Reset", "about_menu": "About...", "export_menu": "Export Notes to Markdown...", "restore_menu": "Restore from Backup...",
                "exit_menu": "Exit", "add_list_menu": "Add List...", "rename_list_menu": "Rename List...", "delete_list_menu": "Delete List...",
                "new_list_prompt": "Enter new list name:", "rename_list_prompt": "Enter new list name:", "delete_list_confirm": "Are you sure you want to delete list '{list_name}'?",
                "settings_title": "Settings", "settings_tab_general": "General", "settings_tab_appearance": "Appearance", "settings_tab_zen": "Zen Editor",
                "settings_lang_label": "Language:", "settings_theme_label": "Main theme:", "settings_light_theme": "Light", "settings_dark_theme": "Dark",
                "settings_trigger_pos_label": "Button position:", "settings_trigger_left": "Left", "settings_trigger_right": "Right", "settings_accent_color_label": "Accent color:",
                "settings_choose_color_btn": "Choose color...", "settings_light_theme_bg_label": "Light theme BG:", "settings_light_theme_text_label": "Light theme Text:",
                "settings_dark_theme_bg_label": "Dark theme BG:", "settings_dark_theme_text_label": "Dark theme Text:", "settings_light_theme_list_text_label": "List text (light):",
                "settings_dark_theme_list_text_label": "List text (dark):", "settings_zen_bg_label": "Zen Background (image):", "settings_browse_btn": "Browse...",
                "settings_clear_btn": "Clear", "settings_transparent_editor": "Transparent editor", "settings_font_label": "Font", "settings_size_label": "Size:",
                "settings_font_color_label": "Font Color:", "settings_alignment_label": "Alignment:", "settings_align_left": "Left", "settings_align_justify": "Justify",
                "settings_padding_horiz": "Horiz. Padding (%):", "settings_padding_vert": "Vert. Padding (%):", "settings_first_line_indent": "1st line indent (px):",
                "task_menu_edit": "Edit...", "task_menu_toggle_completed": "Toggle completed", "note_pin_menu": "Pin", "note_unpin_menu": "Unpin",
                "list_management_tooltip": "Right-click to manage lists", "open_window_menu": "Open window mode…", "open_window_tooltip": "Open in window mode",
                "left_column_toggle": "List", "left_column_tooltip": "Show/hide notes list", "right_column_toggle": "Tasks", "right_column_tooltip": "Show/hide tasks",
                "to_panel_button": "⇦ Panel", "to_panel_tooltip": "Open side panel", "tags_label": "Tags:", "to_task_btn": "➕ to tasks",
                "to_task_tooltip": "Add selected text to tasks", "import_settings": "Import settings…", "export_settings": "Export settings…",
                "task_templates_title": "Task templates", "task_templates_hint": "One template per line:", "settings_enable_tree": "Tree notes (beta)",
                "tree_new_folder": "New folder...", "tree_rename_folder": "Rename folder...",
                "tree_delete_folder": "Delete folder", "tree_delete_note": "Delete note", "tree_new_note_here": "New note here",
                "tree_confirm_delete_folder": "Delete folder '{name}' with all contents?",
                "settings_audio_folder_label": "Music folder:", "audio_toggle_tooltip": "Music", "audio_prev": "Previous", "audio_next": "Next",
                "audio_play": "Play", "audio_pause": "Pause", "audio_stop": "Stop", "audio_volume": "Volume", "settings_zen_audio_folder_label": "Music Zen:",
                "new_note_title": "New Note", "folder_description": "Folder description", "note_editing": "Editing note",
                "settings_zen_light_theme_bg_label": "Zen BG (light theme):",
                "settings_zen_dark_theme_bg_label": "Zen BG (dark theme):",
                "settings_min_width_left": "Min. left column width:",
                "settings_min_width_right": "Min. right column width:",
                "task_filter_all": "All",
                "task_filter_active": "Active",
                "task_filter_completed": "Completed",
                "settings_min_width_left": "Min. left column width:",
                "settings_min_width_right": "Min. right column width:",
                "settings_padding_top": "Padding Top (px):",
                "settings_padding_bottom": "Padding Bottom (px):",
                "settings_padding_left": "Padding Left (px):",
                "settings_padding_right": "Padding Right (px):",
                "backup_manager_title": "Backup Manager",
                "backup_available_copies": "Available copies:",
                "backup_restore_btn": "Restore",
                "backup_delete_btn": "Delete",
                "backup_no_copies": "No backups found.",
                "backup_confirm_restore": "Are you sure you want to restore data from the copy dated {date}?",
                "backup_confirm_delete": "Are you sure you want to delete this backup?",
                "settings_min_width_left": "Min. left column width:",
                "settings_min_width_right": "Min. right column width:",
                "settings_padding_top": "Padding Top (px):",
                "settings_padding_bottom": "Padding Bottom (px):",
                "settings_padding_left": "Padding Left (px):",
                "settings_padding_right": "Padding Right (px):",
                "settings_create_backup_now": "Create backup now",
                "zen_button_tooltip": "Enter Zen Mode (fullscreen editor)",
                "window_button_tooltip": "Switch to Window Mode",
                "backup_confirm_delete": "Are you sure you want to delete this backup?",
            }
            with open(en_path, 'w', encoding='utf-8') as f:
                json.dump(en_data, f, ensure_ascii=False, indent=2)

    def _scan_languages(self):
        langs = {}
        if not os.path.isdir(self.locales_dir): return {}
        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                lang_code = os.path.splitext(filename)[0]
                try:
                    with open(os.path.join(self.locales_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        langs[lang_code] = data.get("lang_name", lang_code)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Could not load language file {filename}: {e}")
        return langs

    def set_language(self, lang_code):
        path = os.path.join(self.locales_dir, f"{lang_code}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                if self.current_lang != lang_code:
                    self.current_lang = lang_code
                    self.language_changed.emit()
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading language {lang_code}: {e}")
                if lang_code != 'en_US': self.set_language('en_US')
        else:
            print(f"Language file for {lang_code} not found.")

    def get(self, key, default_text=""):
        return self.translations.get(key, default_text or key)

# --- Редактор с хоткеем Shift+Enter ---
class NoteEditor(QTextEdit):
    save_and_new_requested = pyqtSignal()
    
    def __init__(self, parent_panel=None, parent=None):
        super().__init__(parent)
        self.parent_panel = parent_panel

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.save_and_new_requested.emit()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        standard_menu = self.createStandardContextMenu()
        
        if self.parent_panel and hasattr(self.parent_panel.main_parent, '_create_themed_menu'):
            themed_menu = self.parent_panel.main_parent._create_themed_menu()
            themed_menu.addActions(standard_menu.actions())
            themed_menu.exec(event.globalPos())
        else:
            standard_menu.exec(event.globalPos())

# --- О программе ---
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.loc = parent.loc if hasattr(parent, 'loc') else LocalizationManager()
        self.setFixedSize(480, 550)
        
        self.main_layout = QVBoxLayout(self)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setOpenExternalLinks(True)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.info_label)
        self.main_layout.addWidget(scroll_area)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.buttons.accepted.connect(self.accept)
        self.main_layout.addWidget(self.buttons)

        settings = parent.get_settings() if hasattr(parent, 'get_settings') else {}
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; }}
            QLabel {{ color: {text}; }}
            QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{ border-color: {accent}; }}
        """)
        
        self.retranslate_ui()
        # --- НАЧАЛО БЛОКА СТИЛИЗАЦИИ (убедись, что он здесь) ---
        settings = parent.get_settings() if hasattr(parent, 'get_settings') else {}
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; }}
            QLabel, QScrollArea {{ 
                color: {text}; 
                background-color: transparent; 
            }}
            QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{ border-color: {accent}; }}
        """)

    def retranslate_ui(self):
        self.setWindowTitle(self.loc.get("about_menu", "About..."))
        self.info_label.setText(
            "<h3>Ассистент v2.0</h3>"
            "<p>Эта программа была создана в рамках совместной работы пользователя и AI-ассистентов.</p>"
            "<p><b>Разработчик:</b> Rintaru123</p>"
            "<p><b>AI-ассистенты:</b> Claude 3, ChatGPT, Google AI</p>"
            "<hr>"
            "<h4>Лицензии используемых компонентов:</h4>"
            "<p>Программа написана с использованием фреймворка <b>PyQt6</b> (<b>GPL v3</b>)</p>"
            "<p>Лицензия кода <b>MIT</b>.</p>"
            "<p>Иконки предоставлены Qt Framework и <a target='_blank' href='https://icons8.com'>Icons8</a>.</p>"
            "<hr>"
            "<h4>Лицензии на аудиоматериалы:</h4>"
            
            "<p>Purple Dream by Ghostrifter <a target='_blank' href='https://bit.ly/ghostrifter-yt'>bit.ly/ghostrifter-yt</a><br>"
            "Creative Commons — Attribution-NoDerivs 3.0 Unported — CC BY-ND 3.0<br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/ </a></p>"
            
            "<p>Transcendence by Alexander Nakarada | <a target='_blank' href='https://creatorchords.com'>https://creatorchords.com</a><br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/</a><br>"
            "Creative Commons CC BY 4.0</p>"

            "<p>Meanwhile by Scott Buckley | <a target='_blank' href='http://www.scottbuckley.com.au'>www.scottbuckley.com.au</a><br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/</a><br>"
            "Creative Commons CC BY 4.0</p>"
            
            "<p>Shadows And Dust by Scott Buckley | <a target='_blank' href='http://www.scottbuckley.com.au'>www.scottbuckley.com.au</a><br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/</a><br>"
            "Creative Commons CC BY 4.0</p>"
            
            "<p>Silent Wood by Purrple Cat | <a target='_blank' href='https://purrplecat.com/'>https://purrplecat.com/</a><br>"
            "Music promoted by <a target='_blank' href='https://www.chosic.com/free-music/all/'>https://www.chosic.com/free-music/all/</a><br>"
            "Creative Commons CC BY-SA 3.0</p>"
            "<p><a target='_blank' href='https://icons8.com/icon/gkW5yexEuzan/left-handed'>Левша</a> иконка от <a target='_blank' href='https://icons8.com'>Icons8</a></p>"
        )


class TasksPanel(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__()
        self.data_manager = data_manager
        self.loc = data_manager.loc_manager
        self.main_parent = parent
        self.task_lists = {}
        self.current_list_name = ""
        self.list_names = []
        
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(10)
        
        add_task_layout = QHBoxLayout()
        self.task_input = ThemedLineEdit(main_parent=self.main_parent) 
        self.add_button = QPushButton()
        self.add_button.clicked.connect(self.add_task_from_input)
        self.task_input.returnPressed.connect(self.add_task_from_input)
        self.templates_btn = QToolButton(); self.templates_btn.setText("⋮")
        self.templates_btn.clicked.connect(self.show_templates_menu)
        add_task_layout.addWidget(self.task_input, 1)
        add_task_layout.addWidget(self.templates_btn)
        add_task_layout.addWidget(self.add_button)
        
        list_mgmt_layout = QHBoxLayout(); list_mgmt_layout.setSpacing(5)
        self.prev_list_btn = QPushButton("<")
        self.prev_list_btn.clicked.connect(lambda: self.switch_list(-1))
        self.list_name_label = QLabel(); self.list_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_name_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_name_label.customContextMenuRequested.connect(self.show_list_context_menu)
        self.next_list_btn = QPushButton(">")
        self.next_list_btn.clicked.connect(lambda: self.switch_list(1))
        
        self.task_filter_combo = QComboBox()
        self.task_filter_combo.currentIndexChanged.connect(self.filter_tasks)
        
        ### ИЗМЕНЕНИЕ: Устанавливаем фиксированную высоту ###
        target_height = 34
        self.prev_list_btn.setFixedSize(target_height, target_height)
        self.next_list_btn.setFixedSize(target_height, target_height)
        self.task_filter_combo.setFixedHeight(target_height)

        list_mgmt_layout.addWidget(self.prev_list_btn)
        list_mgmt_layout.addWidget(self.list_name_label, 1)
        list_mgmt_layout.addWidget(self.next_list_btn)
        list_mgmt_layout.addStretch()
        list_mgmt_layout.addWidget(self.task_filter_combo)
        
        self.task_list_widget = QListWidget(); self.task_list_widget.setObjectName("TaskList")
        self.task_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list_widget.customContextMenuRequested.connect(self.show_task_context_menu)
        self.task_list_widget.itemDoubleClicked.connect(self.edit_task)
        self.task_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.task_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.task_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.task_list_widget.itemChanged.connect(self.on_task_item_changed)
        
        layout.addLayout(add_task_layout)
        layout.addLayout(list_mgmt_layout)
        layout.addWidget(self.task_list_widget)

    def _get_templates(self):
        return self.data_manager.get_settings().get("task_templates", [])

    def _set_templates(self, templates):
        settings = self.data_manager.get_settings()
        settings["task_templates"] = templates
        self.data_manager.save_settings()

    def _create_themed_menu(self):
        if self.main_parent and hasattr(self.main_parent, '_create_themed_menu'):
            return self.main_parent._create_themed_menu()
        return QMenu(self)

    def show_templates_menu(self):
        menu = self._create_themed_menu()
        templates = self._get_templates()
        if templates:
            for t in templates:
                action_text = f"{self.loc.get('add_task_button')}: {t}"
                menu.addAction(action_text, lambda tt=t: self._add_template_task(tt))
            menu.addSeparator()
        menu.addAction(self.loc.get('task_templates_title', 'Управление шаблонами…'), self._manage_templates)
        menu.exec(self.templates_btn.mapToGlobal(QPoint(0, self.templates_btn.height())))

    def _add_template_task(self, t):
        self.add_task(t)
        self.data_manager.save_app_data()
        
    def _manage_templates(self):
        dlg = TemplatesDialog(self, self.data_manager.get_settings(), self.loc)
        dlg.set_templates(self._get_templates())
        if dlg.exec():
            new_list = dlg.get_templates()
            self._set_templates(new_list)

    def on_task_item_changed(self, item):
        if not item: return
        task_data = item.data(Qt.ItemDataRole.UserRole) or {}
        completed = item.checkState() == Qt.CheckState.Checked
        if task_data.get("completed") != completed:
            task_data["completed"] = completed
            item.setData(Qt.ItemDataRole.UserRole, task_data)
            self.update_task_item_style(item)
            self.filter_tasks()
            self.data_manager.save_app_data()

    def retranslate_ui(self):
        self.add_button.setText(self.loc.get("add_task_button"))
        self.task_input.setPlaceholderText(self.loc.get("new_task_placeholder"))
        
        current_index = self.task_filter_combo.currentIndex()
        self.task_filter_combo.blockSignals(True)
        self.task_filter_combo.clear()
        self.task_filter_combo.addItem(self.loc.get("task_filter_all", "Все"))
        self.task_filter_combo.addItem(self.loc.get("task_filter_active", "Активные"))
        self.task_filter_combo.addItem(self.loc.get("task_filter_completed", "Выполненные"))
        self.task_filter_combo.setCurrentIndex(current_index if current_index != -1 else 0)
        self.task_filter_combo.blockSignals(False)
        self.filter_tasks()

        self.list_name_label.setToolTip(self.loc.get("list_management_tooltip"))
        self.templates_btn.setToolTip(self.loc.get("task_templates_title"))

    def add_task(self, text, is_completed=False):
        if not text: return
        item = QListWidgetItem()
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.ItemDataRole.UserRole, {"text": text, "completed": is_completed})
        item.setSizeHint(QSize(0, 32))
        self.task_list_widget.addItem(item)
        self.update_task_item_style(item)
        self.filter_tasks()

    def update_task_item_style(self, item):
        task_data = item.data(Qt.ItemDataRole.UserRole) or {}
        is_completed = task_data.get("completed", False)
        font = item.font()
        font.setStrikeOut(is_completed)
        item.setFont(font)
        
        settings = self.data_manager.get_settings()
        _, _, _, _, list_text_color = theme_colors(settings)
        final_color = QColor(list_text_color)
        if is_completed:
            final_color.setAlpha(120)
        item.setForeground(final_color)
        
        self.task_list_widget.blockSignals(True)
        item.setText(task_data.get("text", ""))
        item.setCheckState(Qt.CheckState.Checked if is_completed else Qt.CheckState.Unchecked)
        self.task_list_widget.blockSignals(False)

    def filter_tasks(self, index=0):
        mode = self.task_filter_combo.currentIndex()
        for i in range(self.task_list_widget.count()):
            item = self.task_list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole):
                is_completed = item.data(Qt.ItemDataRole.UserRole).get("completed", False)
                
                if mode == 0: # Все
                    item.setHidden(False)
                elif mode == 1: # Активные
                    item.setHidden(is_completed)
                elif mode == 2: # Выполненные
                    item.setHidden(not is_completed)

    def add_task_from_input(self):
        task_text = self.task_input.text().strip()
        if task_text:
            self.add_task(task_text)
            self.task_input.clear()
            self.data_manager.save_app_data()

    def show_task_context_menu(self, pos):
        item = self.task_list_widget.itemAt(pos)
        if not item: return
        menu = self._create_themed_menu()
        menu.addAction(self.loc.get("task_menu_edit"), lambda: self.edit_task(item))
        menu.addAction(self.loc.get("task_menu_toggle_completed"), lambda: self.toggle_task_completion(item))
        menu.addSeparator()
        menu.addAction(self.loc.get("delete_task_tooltip"), lambda: self.delete_task(item))
        menu.exec(self.task_list_widget.mapToGlobal(pos))

    def edit_task(self, item):
        if not item: return
        task_data = item.data(Qt.ItemDataRole.UserRole)
        old_text = task_data.get("text", "")
        
        dialog = ThemedInputDialog(
            self, 
            self.loc.get("task_menu_edit"), 
            self.loc.get("rename_list_prompt", "Введите новый текст:"), 
            text=old_text,
            settings=self.data_manager.get_settings()
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_text = dialog.get_text()
            if new_text and new_text.strip() != old_text:
                task_data["text"] = new_text.strip()
                item.setData(Qt.ItemDataRole.UserRole, task_data)
                self.update_task_item_style(item)
                self.data_manager.save_app_data()

    def toggle_task_completion(self, item):
        if not item: return
        is_checked = item.checkState() == Qt.CheckState.Checked
        item.setCheckState(Qt.CheckState.Unchecked if is_checked else Qt.CheckState.Checked)

    def delete_task(self, item):
        row = self.task_list_widget.row(item)
        if row >= 0:
            self.task_list_widget.takeItem(row)
            self.data_manager.save_app_data()

    def get_task_lists_data(self):
        if self.current_list_name:
            current_tasks = []
            for i in range(self.task_list_widget.count()):
                item = self.task_list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole):
                    current_tasks.append(item.data(Qt.ItemDataRole.UserRole))
            self.task_lists[self.current_list_name] = current_tasks
        return self.task_lists

    def load_task_lists(self, task_lists_data, active_list_name):
        self.task_lists = task_lists_data if isinstance(task_lists_data, dict) and task_lists_data else {"Default": []}
        self.list_names = sorted(self.task_lists.keys())
        self.current_list_name = active_list_name if active_list_name in self.list_names else (self.list_names[0] if self.list_names else "")
        self._load_current_list_display()

    def _load_current_list_display(self):
        self.task_list_widget.clear()
        if not self.current_list_name:
            self.list_name_label.setText("")
            return
        self.list_name_label.setText(f"<b>{self.current_list_name}</b>")
        for t in self.task_lists.get(self.current_list_name, []):
            self.add_task(t.get('text', ''), t.get('completed', False))
        self.filter_tasks()

    def switch_list(self, direction):
        if not self.list_names or len(self.list_names) < 2: return
        if self.current_list_name:
            self.task_lists[self.current_list_name] = [self.task_list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.task_list_widget.count())]
        try:
            current_index = self.list_names.index(self.current_list_name)
            new_index = (current_index + direction) % len(self.list_names)
            self.current_list_name = self.list_names[new_index]
            self._load_current_list_display()
            self.data_manager.save_app_data()
        except ValueError:
            self.current_list_name = self.list_names[0]
            self._load_current_list_display()

    def show_list_context_menu(self, pos):
        menu = self._create_themed_menu()
        menu.addAction(self.loc.get("add_list_menu"), self.add_new_list)
        if self.current_list_name:
            menu.addAction(self.loc.get("rename_list_menu"), self.rename_current_list)
        if len(self.list_names) > 1:
            menu.addAction(self.loc.get("delete_list_menu"), self.delete_current_list)
        menu.exec(self.list_name_label.mapToGlobal(pos))

    def add_new_list(self):
        dialog = ThemedInputDialog(
            self,
            self.loc.get("add_list_menu"),
            self.loc.get("new_list_prompt"),
            settings=self.data_manager.get_settings()
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.get_text()
            if text and text not in self.task_lists:
                if self.current_list_name:
                    self.task_lists[self.current_list_name] = [self.task_list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.task_list_widget.count())]
                self.task_lists[text] = []
                self.list_names = sorted(self.task_lists.keys())
                self.current_list_name = text
                self._load_current_list_display()
                self.data_manager.save_app_data()

    def rename_current_list(self):
        old_name = self.current_list_name
        if not old_name: return
        
        dialog = ThemedInputDialog(
            self,
            self.loc.get("rename_list_menu"),
            self.loc.get("rename_list_prompt"),
            text=old_name,
            settings=self.data_manager.get_settings()
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_text()
            if new_name and new_name != old_name and new_name not in self.task_lists:
                self.task_lists[new_name] = self.task_lists.pop(old_name, [])
                self.list_names = sorted(self.task_lists.keys())
                self.current_list_name = new_name
                self.list_name_label.setText(f"<b>{self.current_list_name}</b>")
                self.data_manager.save_app_data()

    def delete_current_list(self):
        if len(self.list_names) <= 1: return
        reply = QMessageBox.question(self, self.loc.get("delete_list_menu"), self.loc.get("delete_list_confirm").format(list_name=self.current_list_name))
        if reply == QMessageBox.StandardButton.Yes:
            try:
                current_index = self.list_names.index(self.current_list_name)
                del self.task_lists[self.current_list_name]
                self.list_names.remove(self.current_list_name)
                new_index = max(0, current_index - 1)
                self.current_list_name = self.list_names[new_index] if self.list_names else ""
                self._load_current_list_display()
                self.data_manager.save_app_data()
            except (ValueError, IndexError) as e:
                print(f"Error deleting list: {e}")

class NotesPanel(QWidget):
    tags_updated = pyqtSignal(set)
    zen_mode_requested = pyqtSignal(str, str)
    note_created = pyqtSignal(str)
    note_deleted = pyqtSignal(str)
    note_saved = pyqtSignal(str)

    def __init__(self, data_manager, parent=None):
        super().__init__()
        self.data_manager = data_manager
        self.loc = data_manager.loc_manager
        self.main_parent = parent
        self.current_note_item = None
        self.saved_text = ""
        self.is_dirty = False
        self.all_tags = set()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(5)

        self.notes_editor_label = QLabel()
        self.notes_editor = NoteEditor(parent_panel=self)
        self.notes_editor.textChanged.connect(self.on_editor_text_changed)
        self.notes_editor.save_and_new_requested.connect(self.handle_save_and_new)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton()
        self.save_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.new_button = QPushButton()
        self.new_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.zen_button = QPushButton()
        
        # ИЗМЕНЕНИЕ: Создаем кнопку "Оконный режим" здесь
        self.window_button = QPushButton()
        self.window_button.setIcon(ThemedIconProvider.icon("window", self.data_manager.get_settings()))
        self.window_button.clicked.connect(self.data_manager.switch_to_window_mode)
        
        self.save_button.clicked.connect(self.save_current_note)
        self.new_button.clicked.connect(lambda: self.clear_for_new_note(force=False))
        self.zen_button.clicked.connect(self.open_zen_mode)
        
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.zen_button)
        # ИЗМЕНЕНИЕ: Добавляем кнопку в компоновку
        button_layout.addWidget(self.window_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)

        filter_layout = QHBoxLayout()
        self.search_input = ThemedLineEdit(main_parent=self.main_parent)
        self.search_input.textChanged.connect(self.filter_notes)
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.currentIndexChanged.connect(self.filter_notes)
        filter_layout.addWidget(self.search_input, 1)
        filter_layout.addWidget(self.tag_filter_combo)

        self.note_list_widget = QListWidget()
        self.note_list_widget.currentItemChanged.connect(self.display_selected_note)
        self.note_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.note_list_widget.customContextMenuRequested.connect(self.show_note_context_menu)

        layout.addWidget(self.notes_editor_label)
        layout.addWidget(self.notes_editor, 1)
        layout.addLayout(button_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.note_list_widget, 1)

        self.autosave_timer = QTimer(self)
        interval_ms = max(2, self.data_manager.get_settings().get("autosave_interval_sec", 10)) * 1000
        self.autosave_timer.setInterval(interval_ms)
        self.autosave_timer.timeout.connect(self.save_if_dirty)
        self.autosave_timer.start()

    def retranslate_ui(self):
        self.notes_editor_label.setText(self.loc.get("notes_editor_label"))
        self.save_button.setText(self.loc.get("save_button"))
        self.new_button.setText(self.loc.get("new_note_button"))
        self.zen_button.setText(self.loc.get("zen_button"))
        
        ### ИЗМЕНЕНИЕ: Добавляем ToolTips ###
        self.zen_button.setToolTip(self.loc.get("zen_button_tooltip"))
        self.window_button.setToolTip(self.loc.get("window_button_tooltip"))
        
        self.search_input.setPlaceholderText(self.loc.get("search_placeholder"))
        self.notes_editor.setPlaceholderText(self.loc.get("new_note_placeholder"))
        
        current_text = self.tag_filter_combo.currentText()
        all_tags_text = self.loc.get("all_tags_combo")

        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItem(all_tags_text)
        self.tag_filter_combo.addItems(sorted(list(self.all_tags)))
        
        idx = self.tag_filter_combo.findText(current_text)
        self.tag_filter_combo.setCurrentIndex(idx if idx != -1 else 0)
        self.tag_filter_combo.blockSignals(False)
        self.filter_notes()

    def _create_themed_menu(self):
        if self.main_parent and hasattr(self.main_parent, '_create_themed_menu'):
            return self.main_parent._create_themed_menu()
        return QMenu(self)

    def show_note_context_menu(self, pos):
        item = self.note_list_widget.itemAt(pos)
        if not item: return
        menu = self._create_themed_menu()
        pin = item.data(Qt.ItemDataRole.UserRole).get("pinned", False)
        pin_text = self.loc.get("note_unpin_menu") if pin else self.loc.get("note_pin_menu")
        menu.addAction(pin_text, lambda: self.toggle_pin(item))
        menu.addSeparator()
        delete_action = QAction(self.loc.get("delete_note_tooltip"), self)
        delete_action.triggered.connect(lambda: self.perform_delete_note(item))
        menu.addAction(delete_action)
        menu.exec(self.note_list_widget.mapToGlobal(pos))
    
    def find_tags(self, text):
        return set(re.findall(r'#(\w+)', text))

    def update_list_item_title_text(self, list_item):
        note_data = list_item.data(Qt.ItemDataRole.UserRole) or {}
        ts = note_data.get("timestamp", "")
        pinned = note_data.get("pinned", False)
        list_item.setText(f"{ts}{' 📌' if pinned else ''}")

    def sort_note_items(self):
        lw = self.note_list_widget
        items_data = []
        for i in range(lw.count()):
            it = lw.item(i)
            nd = it.data(Qt.ItemDataRole.UserRole) or {}
            items_data.append(nd)
        
        lw.clear()
        items_data.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
        items_data.sort(key=lambda d: not d.get("pinned", False))
        
        for note_data in items_data:
            self.add_note_item(note_data)

    def toggle_pin(self, item):
        if not item: return
        nd = item.data(Qt.ItemDataRole.UserRole) or {}
        nd["pinned"] = not nd.get("pinned", False)
        item.setData(Qt.ItemDataRole.UserRole, nd)
        self.update_list_item_title_text(item)
        self.sort_note_items()
        self.data_manager.save_app_data()
    
    def update_tag_filter(self):
        self.retranslate_ui()

    def filter_notes(self):
        search_text = self.search_input.text().lower()
        selected_tag_item_text = self.tag_filter_combo.currentText()
        is_all_tags_selected = selected_tag_item_text == self.loc.get("all_tags_combo")
        
        for i in range(self.note_list_widget.count()):
            item = self.note_list_widget.item(i)
            note_data = item.data(Qt.ItemDataRole.UserRole)
            note_text = note_data.get('text', '')
            note_timestamp = note_data.get('timestamp', '')
            haystack = (note_timestamp + ' ' + note_text).lower()
            
            text_match = search_text in haystack
            tag_match = is_all_tags_selected or (f"#{selected_tag_item_text}" in note_text)
            
            item.setHidden(not (text_match and tag_match))
    
    def display_selected_note(self, current_item, previous_item):
        if previous_item and self.is_dirty:
            self.save_current_note()
        if not current_item:
            if self.current_note_item is not None:
                self.clear_for_new_note(force=True)
            return
        self.current_note_item = current_item
        note_data = self.current_note_item.data(Qt.ItemDataRole.UserRole)
        source_text = note_data.get("text", "")
        self.notes_editor.setPlainText(source_text)
        self.saved_text = source_text
        self.on_editor_text_changed()
    
    def save_current_note(self):
        text = self.notes_editor.toPlainText().strip()
        if not self.current_note_item and not text:
            return
        
        new_tags = self.find_tags(text)
        if new_tags != self.all_tags:
            self.all_tags.update(new_tags)
            self.update_tag_filter()
            self.tags_updated.emit(self.all_tags)

        ts_emit = ""
        if self.current_note_item:
            note_data = self.current_note_item.data(Qt.ItemDataRole.UserRole)
            note_data["text"] = text
            self.current_note_item.setData(Qt.ItemDataRole.UserRole, note_data)
            ts_emit = note_data.get("timestamp", "")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            note_data = {"timestamp": timestamp, "text": text, "pinned": False}
            new_item = self.add_note_item(note_data)
            self.current_note_item = new_item
            self.note_list_widget.blockSignals(True)
            self.note_list_widget.setCurrentItem(new_item)
            self.note_list_widget.blockSignals(False)
            self.note_created.emit(timestamp)
            ts_emit = timestamp

        self.saved_text = text
        self.on_editor_text_changed()
        self.data_manager.save_app_data()
        if ts_emit:
            self.note_saved.emit(ts_emit)
    
    def load_notes(self, notes_data):
        self.note_list_widget.clear()
        self.all_tags.clear()
        if not isinstance(notes_data, list):
            notes_data = []
            
        for note in notes_data:
            note.setdefault("pinned", False)
            self.add_note_item(note)
            self.all_tags.update(self.find_tags(note.get("text", "")))
        
        self.sort_note_items()
        self.update_tag_filter()
        self.tags_updated.emit(self.all_tags)
    
    def open_zen_mode(self):
        self.save_if_dirty()
        text = self.notes_editor.toPlainText()
        timestamp = ""
        if self.current_note_item:
            timestamp = self.current_note_item.data(Qt.ItemDataRole.UserRole).get('timestamp', '')
        self.zen_mode_requested.emit(text, timestamp)
    
    def find_and_select_note_by_timestamp(self, timestamp):
        if not timestamp: return
        for i in range(self.note_list_widget.count()):
            item = self.note_list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) and item.data(Qt.ItemDataRole.UserRole).get('timestamp') == timestamp:
                self.note_list_widget.setCurrentItem(item)
                self.note_list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                break
    
    def clear_for_new_note(self, force=False):
        if not force and self.is_dirty:
            self.save_current_note()
        self.current_note_item = None
        if self.note_list_widget.currentItem() is not None:
            self.note_list_widget.blockSignals(True)
            self.note_list_widget.setCurrentItem(None)
            self.note_list_widget.blockSignals(False)
        self.notes_editor.clear()
        self.saved_text = ""
        self.on_editor_text_changed()
        self.notes_editor.setPlaceholderText(self.loc.get("new_note_placeholder"))
    
    def handle_save_and_new(self):
        self.save_current_note()
        self.clear_for_new_note(force=True)
    
    def on_editor_text_changed(self):
        self.is_dirty = (self.notes_editor.toPlainText().strip() != self.saved_text.strip())
        self.data_manager.main_popup_on_data_changed()
    
    def save_if_dirty(self):
        if self.is_dirty:
            self.save_current_note()
    
    def add_note_item(self, note_data):
        list_item = QListWidgetItem()
        list_item.setData(Qt.ItemDataRole.UserRole, note_data)
        list_item.setSizeHint(QSize(0, 32))
        self.update_list_item_title_text(list_item)
        self.note_list_widget.addItem(list_item)
        return list_item
    
    def perform_delete_note(self, item_to_delete):
        if not item_to_delete: return
        ts = (item_to_delete.data(Qt.ItemDataRole.UserRole) or {}).get("timestamp")
        if not ts: return

        if self.note_list_widget.currentItem() == item_to_delete:
            self.clear_for_new_note(force=True)
        
        row = self.note_list_widget.row(item_to_delete)
        if row >= 0:
            self.note_list_widget.takeItem(row)
            self.note_deleted.emit(ts)
            self.data_manager.delete_note_by_timestamp_from_all_data(ts)

    def delete_note_by_timestamp(self, timestamp):
        if not timestamp: return
        for i in range(self.note_list_widget.count()):
            item = self.note_list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) and item.data(Qt.ItemDataRole.UserRole).get("timestamp") == timestamp:
                self.note_list_widget.takeItem(i)
                return

    def get_notes_data(self):
        return [self.note_list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.note_list_widget.count())]

    def apply_editor_style(self, settings):
        font_family = settings.get("zen_font_family", "Georgia")
        override_size = settings.get("window_editor_font_size", 0)
        font_size = override_size if override_size > 0 else settings.get("zen_font_size", 18)
        
        is_dark = settings.get("theme") == "dark"
        default_color = settings.get("dark_theme_text") if is_dark else settings.get("light_theme_text")
        editor_color = settings.get("zen_font_color") or default_color
        
        alignment = Qt.AlignmentFlag.AlignJustify if settings.get("zen_alignment") == "justify" else Qt.AlignmentFlag.AlignLeft
        indent = settings.get("zen_first_line_indent", 0)
        
        padding_top = settings.get("editor_padding_top", 8)
        padding_bottom = settings.get("editor_padding_bottom", 8)
        padding_left = settings.get("editor_padding_left", 10)
        padding_right = settings.get("editor_padding_right", 10)

        self.notes_editor.setAlignment(alignment)
        
        f = self.notes_editor.font()
        f.setFamily(font_family)
        f.setPointSize(font_size)
        self.notes_editor.setFont(f)
        
        self.notes_editor.setStyleSheet(f"""
            QTextEdit {{ 
                color: {editor_color}; 
                padding-top: {padding_top}px;
                padding-bottom: {padding_bottom}px;
                padding-left: {padding_left}px;
                padding-right: {padding_right}px;
            }}
        """)
        
        cursor = self.notes_editor.textCursor()
        block_format = cursor.blockFormat()
        block_format.setTextIndent(indent)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(block_format)
        cursor.clearSelection()
        self.notes_editor.setTextCursor(cursor)

class TemplatesDialog(QDialog):
    def __init__(self, parent, settings, loc_manager):
        super().__init__(parent)
        self.settings = settings
        self.loc = loc_manager
        self.setWindowTitle(self.loc.get("task_templates_title"))
        self.resize(520, 460)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        
        self.info_label = QLabel(self.loc.get("task_templates_hint"))
        layout.addWidget(self.info_label)
        
        self.edit = QPlainTextEdit()
        self.edit.setTabChangesFocus(True)
        layout.addWidget(self.edit, 1)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(btns)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        
        self.apply_theme(self.settings)

    def set_templates(self, items):
        self.edit.setPlainText("\n".join(items))

    def get_templates(self):
        return [line.strip() for line in self.edit.toPlainText().splitlines() if line.strip()]

    def apply_theme(self, settings):
        is_dark, _, bg, text, _ = theme_colors(settings)
        component_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border_color = "#555" if is_dark else "#ced4da"
        hover = QColor(component_bg).lighter(110).name()
        self.setStyleSheet(f"""
            QDialog{{background-color:{bg};color:{text};}}
            QLabel{{background:transparent;color:{text};}}
            QPlainTextEdit{{background-color:{component_bg};color:{text};border:1px solid {border_color};border-radius:6px;padding:6px;}}
            QPushButton{{background-color:{component_bg};color:{text};border:1px solid {border_color};border-radius:6px;padding:6px 12px;}}
            QPushButton:hover{{background-color:{hover};}}
            QDialogButtonBox{{background:transparent;}}
        """)

class SettingsPanel(QWidget):
    settings_changed = pyqtSignal(dict)

    def __init__(self, current_settings, loc_manager, parent=None, context="main_popup"):
        super().__init__(parent)
        self.settings = current_settings.copy()
        self.loc = loc_manager
        self.context = context
        
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addStretch()
        
        self.container_frame = QFrame()
        self.container_frame.setObjectName("SettingsPanelFrame")
        outer_layout.addWidget(self.container_frame)
        outer_layout.addStretch()

        main_layout = QVBoxLayout(self.container_frame)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        title_layout = QHBoxLayout()
        self.title_label = QLabel()
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setObjectName("settingsCloseBtn")
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        main_layout.addLayout(title_layout)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        self.color_widgets = {}
        
        self.general_tab = self.create_general_tab()
        self.appearance_tab = self.create_appearance_tab()
        self.zen_tab = self.create_zen_editor_tab()
        self.font_tab = self.create_font_tab()

        self.tab_widget.addTab(self.general_tab, "")
        self.tab_widget.addTab(self.appearance_tab, "")
        self.tab_widget.addTab(self.zen_tab, "")
        self.tab_widget.addTab(self.font_tab, "")

        self.configure_tabs_visibility()

        self.load_settings_to_ui()
        self.connect_signals()
        self.retranslate_ui()
        self.apply_styles()

    def configure_tabs_visibility(self):
        is_zen_visible = (self.context == "zen_mode")
        self.tab_widget.setTabVisible(2, is_zen_visible)
        if hasattr(self, 'splitter_settings_container'):
             self.splitter_settings_container.setVisible(self.context == "window_main")

    ### ВОЗВРАЩЕННЫЙ МЕТОД ###
    def set_splitter_settings_visible(self, visible):
        """Показывает или скрывает настройки сплиттера."""
        if hasattr(self, 'splitter_settings_container'):
            self.splitter_settings_container.setVisible(visible)

    def create_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.lang_label = QLabel()
        self.lang_list_widget = QListWidget()
        self.lang_list_widget.setFixedHeight(120)
        layout.addWidget(self.lang_label)
        layout.addWidget(self.lang_list_widget)
        
        self.theme_group = QButtonGroup(self)
        theme_box = QHBoxLayout()
        self.theme_label = QLabel()
        self.main_dark_radio = QRadioButton()
        self.main_light_radio = QRadioButton()
        self.theme_group.addButton(self.main_dark_radio)
        self.theme_group.addButton(self.main_light_radio)
        theme_box.addWidget(self.theme_label)
        theme_box.addWidget(self.main_light_radio)
        theme_box.addWidget(self.main_dark_radio)
        theme_box.addStretch()
        layout.addLayout(theme_box)
        
        self.pos_group = QButtonGroup(self)
        pos_box = QHBoxLayout()
        self.pos_label = QLabel()
        self.trigger_left_radio = QRadioButton()
        self.trigger_right_radio = QRadioButton()
        self.pos_group.addButton(self.trigger_left_radio)
        self.pos_group.addButton(self.trigger_right_radio)
        pos_box.addWidget(self.pos_label)
        pos_box.addWidget(self.trigger_left_radio)
        pos_box.addWidget(self.trigger_right_radio)
        pos_box.addStretch()
        layout.addLayout(pos_box)
        
        audio_row = QHBoxLayout()
        self.audio_label = QLabel()
        self.audio_path_edit = QLineEdit()
        self.audio_browse_btn = QPushButton()
        self.audio_clear_btn = QPushButton()
        audio_row.addWidget(self.audio_label)
        audio_row.addWidget(self.audio_path_edit, 1)
        audio_row.addWidget(self.audio_browse_btn)
        audio_row.addWidget(self.audio_clear_btn)
        layout.addLayout(audio_row)
        
        layout.addStretch()
        self.create_backup_btn = QPushButton()
        layout.addWidget(self.create_backup_btn, 0, Qt.AlignmentFlag.AlignCenter)
        return tab

    def create_appearance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        def create_color_picker(setting_key):
            h_layout = QHBoxLayout()
            label = QLabel()
            swatch = QLabel(); swatch.setFixedSize(20, 20); swatch.setStyleSheet("border: 1px solid #888;")
            btn = QPushButton()
            h_layout.addWidget(label, 1)
            h_layout.addWidget(swatch)
            h_layout.addWidget(btn)
            self.color_widgets[setting_key] = (label, swatch, btn)
            return h_layout

        for key in ["accent_color", "light_theme_bg", "light_theme_text", "light_theme_list_text", "dark_theme_bg", "dark_theme_text", "dark_theme_list_text"]:
            layout.addLayout(create_color_picker(key))
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        self.splitter_settings_container = QWidget()
        splitter_layout = QVBoxLayout(self.splitter_settings_container)
        splitter_layout.setContentsMargins(0,0,0,0)

        self.min_width_left_label = QLabel()
        self.min_width_left_spin = QSpinBox()
        self.min_width_left_spin.setRange(150, 500)
        self.min_width_left_spin.setSuffix(" px")
        width_layout_left = QHBoxLayout()
        width_layout_left.addWidget(self.min_width_left_label)
        width_layout_left.addWidget(self.min_width_left_spin)
        splitter_layout.addLayout(width_layout_left)

        self.min_width_right_label = QLabel()
        self.min_width_right_spin = QSpinBox()
        self.min_width_right_spin.setRange(250, 600)
        self.min_width_right_spin.setSuffix(" px")
        width_layout_right = QHBoxLayout()
        width_layout_right.addWidget(self.min_width_right_label)
        width_layout_right.addWidget(self.min_width_right_spin)
        splitter_layout.addLayout(width_layout_right)
        
        layout.addWidget(self.splitter_settings_container)
        
        layout.addStretch()
        return tab

    def create_zen_editor_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        def create_color_picker(setting_key):
            h_layout = QHBoxLayout(); label = QLabel(); swatch = QLabel(); swatch.setFixedSize(20, 20); swatch.setStyleSheet("border: 1px solid #888;"); btn = QPushButton()
            h_layout.addWidget(label, 1); h_layout.addWidget(swatch); h_layout.addWidget(btn); self.color_widgets[setting_key] = (label, swatch, btn); return h_layout

        layout.addLayout(create_color_picker("zen_light_theme_bg"))
        layout.addLayout(create_color_picker("zen_dark_theme_bg"))
        
        separator = QFrame(); separator.setFrameShape(QFrame.Shape.HLine); separator.setFrameShadow(QFrame.Shadow.Sunken); layout.addWidget(separator)
        
        bg_layout = QHBoxLayout(); self.zen_bg_label = QLabel(); self.bg_path_edit = QLineEdit(); self.browse_button = QPushButton(); self.clear_bg_button = QPushButton(); btns_h = QHBoxLayout(); btns_h.setSpacing(6); btns_h.addWidget(self.browse_button); btns_h.addWidget(self.clear_bg_button); bg_layout.addWidget(self.zen_bg_label); bg_layout.addWidget(self.bg_path_edit, 1); bg_layout.addLayout(btns_h); layout.addLayout(bg_layout)
        
        opacity_layout = QHBoxLayout(); self.zen_opacity_label = QLabel(); self.zen_opacity_slider = QSlider(Qt.Orientation.Horizontal); self.zen_opacity_slider.setRange(0, 100); self.zen_opacity_value_label = QLabel("100%"); self.zen_opacity_value_label.setMinimumWidth(40); opacity_layout.addWidget(self.zen_opacity_label); opacity_layout.addWidget(self.zen_opacity_slider); opacity_layout.addWidget(self.zen_opacity_value_label); layout.addLayout(opacity_layout)

        padding_block = QVBoxLayout(); row_h = QHBoxLayout(); self.horiz_pad_label = QLabel(); self.horiz_padding = QSpinBox(); self.horiz_padding.setRange(0, 40); row_h.addWidget(self.horiz_pad_label); row_h.addWidget(self.horiz_padding); row_v = QHBoxLayout(); self.vert_pad_label = QLabel(); self.vert_padding = QSpinBox(); self.vert_padding.setRange(0, 40); row_v.addWidget(self.vert_pad_label); row_v.addWidget(self.vert_padding); padding_block.addLayout(row_h); padding_block.addLayout(row_v); layout.addLayout(padding_block)
        
        layout.addStretch()
        return tab
        
    def create_font_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab)
        
        self.font_label = QLabel(); self.font_list_widget = QListWidget()
        
        self.font_search_edit = QLineEdit(); self.font_search_edit.setPlaceholderText("Поиск шрифта..."); self.font_search_edit.textChanged.connect(self._filter_fonts)
        
        layout.addWidget(self.font_label); layout.addWidget(self.font_search_edit); layout.addWidget(self.font_list_widget, 1)

        size_color_layout = QHBoxLayout(); self.size_label = QLabel(); self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(8, 72); size_color_layout.addWidget(self.size_label); size_color_layout.addWidget(self.font_size_spin); size_color_layout.addStretch(); self.font_color_label = QLabel(); self.zen_font_color_swatch = QLabel(); self.zen_font_color_swatch.setFixedSize(20, 20); self.zen_font_color_swatch.setStyleSheet("border: 1px solid #888;"); self.font_color_btn = QPushButton(); self.clear_font_color_btn = QPushButton(); size_color_layout.addWidget(self.font_color_label); size_color_layout.addWidget(self.zen_font_color_swatch); size_color_layout.addWidget(self.font_color_btn); size_color_layout.addWidget(self.clear_font_color_btn); layout.addLayout(size_color_layout)

        self.zen_align_group = QButtonGroup(self); align_layout = QHBoxLayout(); self.align_label = QLabel(); self.align_left_radio = QRadioButton(); self.align_justify_radio = QRadioButton(); self.zen_align_group.addButton(self.align_left_radio); self.zen_align_group.addButton(self.align_justify_radio); align_layout.addWidget(self.align_label); align_layout.addWidget(self.align_left_radio); align_layout.addWidget(self.align_justify_radio); align_layout.addStretch(); layout.addLayout(align_layout)
        
        indent_layout = QHBoxLayout(); 
        self.indent_label = QLabel(); 
        self.first_line_indent_spin = QSpinBox(); 
        self.first_line_indent_spin.setRange(0, 200); 
        self.first_line_indent_spin.setSuffix(" px"); 
        indent_layout.addWidget(self.indent_label); 
        indent_layout.addWidget(self.first_line_indent_spin); 
        indent_layout.addStretch(); 
        layout.addLayout(indent_layout)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        padding_grid = QGridLayout()
        padding_grid.setSpacing(10)
        
        self.padding_top_label = QLabel()
        self.padding_top_spin = QSpinBox()
        self.padding_top_spin.setRange(0, 100)
        padding_grid.addWidget(self.padding_top_label, 0, 0)
        padding_grid.addWidget(self.padding_top_spin, 0, 1)

        self.padding_bottom_label = QLabel()
        self.padding_bottom_spin = QSpinBox()
        self.padding_bottom_spin.setRange(0, 100)
        padding_grid.addWidget(self.padding_bottom_label, 0, 2)
        padding_grid.addWidget(self.padding_bottom_spin, 0, 3)

        self.padding_left_label = QLabel()
        self.padding_left_spin = QSpinBox()
        self.padding_left_spin.setRange(0, 100)
        padding_grid.addWidget(self.padding_left_label, 1, 0)
        padding_grid.addWidget(self.padding_left_spin, 1, 1)

        self.padding_right_label = QLabel()
        self.padding_right_spin = QSpinBox()
        self.padding_right_spin.setRange(0, 100)
        padding_grid.addWidget(self.padding_right_label, 1, 2)
        padding_grid.addWidget(self.padding_right_spin, 1, 3)
        
        layout.addLayout(padding_grid)
        
        return tab

    def _filter_fonts(self, text):
        text = text.lower()
        for i in range(self.font_list_widget.count()):
            item = self.font_list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def load_settings_to_ui(self):
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QListWidget, QSpinBox, QCheckBox, QLineEdit, QRadioButton)):
                widget.blockSignals(True)
        
        self.lang_list_widget.clear()
        current_lang_code = self.settings.get("language", "ru_RU")
        for code, name in self.loc.available_languages.items():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, code)
            self.lang_list_widget.addItem(item)
            if code == current_lang_code:
                self.lang_list_widget.setCurrentItem(item)
                self.lang_list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)

        self.font_list_widget.clear()
        self.all_fonts = sorted(list(set(QFontDatabase.families())))
        self.font_list_widget.addItems(self.all_fonts)
        current_font = self.settings.get("zen_font_family", "Georgia")
        items = self.font_list_widget.findItems(current_font, Qt.MatchFlag.MatchExactly)
        if items:
            self.font_list_widget.setCurrentItem(items[0])
            self.font_list_widget.scrollToItem(items[0], QAbstractItemView.ScrollHint.PositionAtCenter)

        (self.main_light_radio if self.settings.get("theme") == "light" else self.main_dark_radio).setChecked(True)
        (self.trigger_left_radio if self.settings.get("trigger_pos") == "left" else self.trigger_right_radio).setChecked(True)
        self.bg_path_edit.setText(self.settings.get("zen_bg_path", ""))
        
        opacity = self.settings.get("zen_editor_opacity", 85)
        self.zen_opacity_slider.setValue(opacity)
        self.zen_opacity_value_label.setText(f"{opacity}%")
        
        self.font_size_spin.setValue(self.settings.get("zen_font_size", 18))
        (self.align_left_radio if self.settings.get("zen_alignment", "left") == "left" else self.align_justify_radio).setChecked(True)
        self.horiz_padding.setValue(self.settings.get("zen_padding_horiz", 15))
        self.vert_padding.setValue(self.settings.get("zen_padding_vert", 10))
        self.first_line_indent_spin.setValue(self.settings.get("zen_first_line_indent", 0))
        
        self.padding_top_spin.setValue(self.settings.get("editor_padding_top", 8))
        self.padding_bottom_spin.setValue(self.settings.get("editor_padding_bottom", 8))
        self.padding_left_spin.setValue(self.settings.get("editor_padding_left", 10))
        self.padding_right_spin.setValue(self.settings.get("editor_padding_right", 10))


        self.min_width_left_spin.setValue(self.settings.get("window_min_width_left", 260))
        self.min_width_right_spin.setValue(self.settings.get("window_min_width_right", 380))
        
        self.audio_path_edit.setText(self.settings.get("audio_folder", ""))
        
        self.update_color_swatches()
        
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QListWidget, QSpinBox, QCheckBox, QLineEdit, QRadioButton)):
                widget.blockSignals(False)

    def connect_signals(self):
        self.lang_list_widget.currentItemChanged.connect(self._on_language_select)
        self.font_list_widget.currentItemChanged.connect(self.apply_changes)
        
        self.theme_group.buttonClicked.connect(self.apply_changes)
        self.pos_group.buttonClicked.connect(self.apply_changes)
        
        for key, (_, _, btn) in self.color_widgets.items():
            btn.clicked.connect(lambda _, k=key: self.choose_color(k))
        
        self.bg_path_edit.editingFinished.connect(self.apply_changes)
        self.browse_button.clicked.connect(self.browse_for_image)
        self.clear_bg_button.clicked.connect(self.clear_background)
        
        self.zen_opacity_slider.valueChanged.connect(self.apply_changes)
        self.zen_opacity_slider.valueChanged.connect(lambda v: self.zen_opacity_value_label.setText(f"{v}%"))
        
        self.font_size_spin.valueChanged.connect(self.apply_changes)
        self.font_color_btn.clicked.connect(lambda: self.choose_color("zen_font_color"))
        self.clear_font_color_btn.clicked.connect(self.clear_font_color)
        self.zen_align_group.buttonClicked.connect(self.apply_changes)
        self.horiz_padding.valueChanged.connect(self.apply_changes)
        self.vert_padding.valueChanged.connect(self.apply_changes)
        self.first_line_indent_spin.valueChanged.connect(self.apply_changes)

        self.padding_top_spin.valueChanged.connect(self.apply_changes)
        self.padding_bottom_spin.valueChanged.connect(self.apply_changes)
        self.padding_left_spin.valueChanged.connect(self.apply_changes)
        self.padding_right_spin.valueChanged.connect(self.apply_changes)
        
        self.audio_path_edit.editingFinished.connect(self.apply_changes)
        self.audio_browse_btn.clicked.connect(self._browse_audio_folder)
        self.audio_clear_btn.clicked.connect(self._clear_audio_folder)
        
        self.min_width_left_spin.valueChanged.connect(self.apply_changes)
        self.min_width_right_spin.valueChanged.connect(self.apply_changes)
        if hasattr(self.parent().data_manager, 'create_backup'):
            self.create_backup_btn.clicked.connect(self.parent().data_manager.create_backup)

    def retranslate_ui(self):
        self.title_label.setText(f"<b>{self.loc.get('settings_title')}</b>")
        self.tab_widget.setTabText(0, self.loc.get("settings_tab_general"))
        self.tab_widget.setTabText(1, self.loc.get("settings_tab_appearance"))
        self.tab_widget.setTabText(2, self.loc.get("settings_tab_zen"))
        self.tab_widget.setTabText(3, self.loc.get("settings_font_label"))
        
        self.lang_label.setText(self.loc.get("settings_lang_label"))
        self.theme_label.setText(self.loc.get("settings_theme_label"))
        self.main_light_radio.setText(self.loc.get("settings_light_theme"))
        self.main_dark_radio.setText(self.loc.get("settings_dark_theme"))
        self.pos_label.setText(self.loc.get("settings_trigger_pos_label"))
        self.trigger_left_radio.setText(self.loc.get("settings_trigger_left"))
        self.trigger_right_radio.setText(self.loc.get("settings_trigger_right"))
        
        btn_text = self.loc.get("settings_choose_color_btn")
        for key, (label, _, btn) in self.color_widgets.items():
            label.setText(self.loc.get(f"settings_{key}_label", key))
            btn.setText(btn_text)
            
        self.min_width_left_label.setText(self.loc.get("settings_min_width_left"))
        self.min_width_right_label.setText(self.loc.get("settings_min_width_right"))
            
        self.zen_bg_label.setText(self.loc.get("settings_zen_bg_label"))
        self.browse_button.setText(self.loc.get("settings_browse_btn"))
        self.clear_bg_button.setText(self.loc.get("settings_clear_btn"))
        self.zen_opacity_label.setText(self.loc.get("settings_zen_opacity_label", "Прозрачность редактора (%):"))
        
        self.font_label.setText(self.loc.get("settings_font_label"))
        self.size_label.setText(self.loc.get("settings_size_label"))
        self.font_color_label.setText(self.loc.get("settings_font_color_label"))
        self.font_color_btn.setText(btn_text)
        self.clear_font_color_btn.setText(self.loc.get("settings_clear_btn"))
        self.align_label.setText(self.loc.get("settings_alignment_label"))
        self.align_left_radio.setText(self.loc.get("settings_align_left"))
        self.align_justify_radio.setText(self.loc.get("settings_align_justify"))
        self.horiz_pad_label.setText(self.loc.get("settings_padding_horiz"))
        self.vert_pad_label.setText(self.loc.get("settings_padding_vert"))
        self.indent_label.setText(self.loc.get("settings_first_line_indent"))

        self.padding_top_label.setText(self.loc.get("settings_padding_top"))
        self.padding_bottom_label.setText(self.loc.get("settings_padding_bottom"))
        self.padding_left_label.setText(self.loc.get("settings_padding_left"))
        self.padding_right_label.setText(self.loc.get("settings_padding_right"))
        
        self.audio_label.setText(self.loc.get("settings_audio_folder_label"))
        self.audio_browse_btn.setText(self.loc.get("settings_browse_btn"))
        self.audio_clear_btn.setText(self.loc.get("settings_clear_btn"))

        self.create_backup_btn.setText(self.loc.get("settings_create_backup_now", "Создать бэкап сейчас"))

    def choose_color(self, setting_key):
        current_color = self.settings.get(setting_key, "#ffffff") or "#ffffff"
        color = QColorDialog.getColor(QColor(current_color), self, "Выберите цвет")
        if color.isValid():
            self.settings[setting_key] = color.name()
            self.update_color_swatches()
            self.apply_changes()
            
    def update_color_swatches(self):
        for key, (_, swatch, _) in self.color_widgets.items():
            swatch.setStyleSheet(f"background-color: {self.settings.get(key)}; border: 1px solid #888;")
        zen_color = self.settings.get("zen_font_color", "") or "#00000000"
        self.zen_font_color_swatch.setStyleSheet(f"background-color: {zen_color}; border: 1px solid #888;")

    def clear_font_color(self):
        self.settings["zen_font_color"] = ""
        self.update_color_swatches()
        self.apply_changes()
        
    def browse_for_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.bg_path_edit.setText(file_path)
            self.apply_changes()

    def clear_background(self):
        self.bg_path_edit.setText("")
        self.apply_changes()
        
    def _browse_audio_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.loc.get("settings_browse_btn"), "")
        if folder:
            self.audio_path_edit.setText(folder)
            self.apply_changes()

    def _clear_audio_folder(self):
        self.audio_path_edit.setText("")
        self.apply_changes()

    def apply_styles(self):
        is_dark, accent, bg_color, text_color, _ = theme_colors(self.settings)
        line_edit_bg = "rgba(0,0,0,0.25)" if is_dark else "rgba(255,255,255,0.7)"
        button_bg = "rgba(80,80,80,1)" if is_dark else "#e1e1e1"
        border_color = "#555" if is_dark else "#b5b5b5"
        
        self.container_frame.setStyleSheet(f"""
            QFrame#SettingsPanelFrame {{
                background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 10px; }}
            #SettingsPanelFrame QWidget {{ background-color: transparent; }}""")
            
        self.setStyleSheet(f"""
            QLabel, QCheckBox, QRadioButton {{ color:{text_color}; background:transparent; }}
            QLineEdit, QListWidget {{
        background-color:{line_edit_bg}; border:1px solid {border_color};
        color:{text_color}; padding:6px; border-radius:4px;
    }}

            QSpinBox {{
                background-color:{line_edit_bg};
                color:{text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 1px; /* Уменьшаем внутренний отступ для лучшего вида */
                padding-right: 20px; /* Оставляем место для кнопок */
            }}

            /* Стилизуем кнопки "вверх" и "вниз" */
            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                width: 18px; /* Ширина области кнопок */
                border-radius: 0px;
                border-left-width: 1px;
                border-left-style: solid;
                border-left-color: {border_color};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {QColor(button_bg).lighter(115).name()};
            }}

            /* Размещаем кнопку "вверх" */
            QSpinBox::up-button {{
                subcontrol-position: top right;
                margin-top: 1px;
            }}

            /* Размещаем кнопку "вниз" */
            QSpinBox::down-button {{
                subcontrol-position: bottom right;
                margin-bottom: 1px;
                border-top-width: 1px; /* Линия-разделитель между кнопками */
                border-top-style: solid;
                border-top-color: {border_color};
            }}
            
            /* Стилизуем стрелки на кнопках */
            QSpinBox::up-arrow {{
                image: url(:/qt-project.org/styles/commonstyle/images/up-arrow-{"light" if is_dark else "dark"}.png);
                width: 10px;
                height: 10px;
            }}
            QSpinBox::down-arrow {{
                image: url(:/qt-project.org/styles/commonstyle/images/down-arrow-{"light" if is_dark else "dark"}.png);
                width: 10px;
                height: 10px;
            }}
            QListWidget::item:selected {{ background-color: {accent}; color: white; }}
            QListWidget::item:hover {{ background-color: rgba(128,128,128,0.1); }}
            QPushButton {{
                background-color:{button_bg}; color:{text_color}; border:1px solid {border_color};
                padding:6px 12px; border-radius:4px;
            }}
            QPushButton:hover {{ background-color:{QColor(button_bg).lighter(115).name()}; }}
            QTabWidget::pane {{ border:1px solid #444; }}
            QTabBar::tab {{
                background:{"rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.05)"};
                color:{text_color}; padding:8px 12px; border-top-left-radius:4px; border-top-right-radius:4px;
            }}
            QTabBar::tab:selected, QTabBar::tab:hover {{
                background:{"rgba(255,255,255,0.18)" if is_dark else "rgba(0,0,0,0.1)"};
            }}
            QFrame#accentBox {{
                border:2px solid {accent}; border-radius:6px;
                background-color:{"rgba(255,255,255,0.12)" if is_dark else "rgba(0,0,0,0.04)"};
            }}
        """)

    def _on_language_select(self):
        item = self.lang_list_widget.currentItem()
        if not item: return
        lang_code = item.data(Qt.ItemDataRole.UserRole)
        if self.loc.current_lang != lang_code:
            self.loc.set_language(lang_code)
        self.apply_changes()

    def apply_changes(self):
        lang_item = self.lang_list_widget.currentItem()
        if lang_item:
            self.settings["language"] = lang_item.data(Qt.ItemDataRole.UserRole)
        
        font_item = self.font_list_widget.currentItem()
        if font_item:
            self.settings["zen_font_family"] = font_item.text()
            
        self.settings["theme"] = "dark" if self.main_dark_radio.isChecked() else "light"
        self.settings["trigger_pos"] = "left" if self.trigger_left_radio.isChecked() else "right"
        self.settings["zen_bg_path"] = self.bg_path_edit.text()
        self.settings["zen_editor_opacity"] = self.zen_opacity_slider.value()
        self.settings["zen_font_size"] = self.font_size_spin.value()
        self.settings["zen_alignment"] = "justify" if self.align_justify_radio.isChecked() else "left"
        self.settings["zen_padding_horiz"] = self.horiz_padding.value()
        self.settings["zen_padding_vert"] = self.vert_padding.value()
        self.settings["zen_first_line_indent"] = self.first_line_indent_spin.value()

        self.settings["editor_padding_top"] = self.padding_top_spin.value()
        self.settings["editor_padding_bottom"] = self.padding_bottom_spin.value()
        self.settings["editor_padding_left"] = self.padding_left_spin.value()
        self.settings["editor_padding_right"] = self.padding_right_spin.value()
        
        self.settings["audio_folder"] = self.audio_path_edit.text().strip()
        self.settings["window_min_width_left"] = self.min_width_left_spin.value()
        self.settings["window_min_width_right"] = self.min_width_right_spin.value()
        
        self.apply_styles()
        self.settings_changed.emit(self.settings.copy())

    def update_splitter_values(self, sizes):
        self.min_width_left_spin.blockSignals(True)
        self.min_width_right_spin.blockSignals(True)
        if len(sizes) == 3:
             self.min_width_left_spin.setValue(sizes[0])
             self.min_width_right_spin.setValue(sizes[2])
        self.min_width_left_spin.blockSignals(False)
        self.min_width_right_spin.blockSignals(False)

class ZenEditor(QTextEdit):
    def __init__(self, parent_window=None, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window

    def contextMenuEvent(self, event):
        standard_menu = self.createStandardContextMenu()
        if self.parent_window and hasattr(self.parent_window, '_create_themed_menu'):
            themed_menu = self.parent_window._create_themed_menu()
            themed_menu.addActions(standard_menu.actions())
            themed_menu.exec(event.globalPos())
        else:
            standard_menu.exec(event.globalPos())


class ZenModeWindow(QWidget):
    zen_exited = pyqtSignal(str)
    zen_saved_and_closed = pyqtSignal(str)
    
    def __init__(self, initial_text, settings, loc_manager, data_manager):
        super().__init__()
        self.setObjectName("ZenModeWindow")
        self.settings = settings
        self.loc = loc_manager
        self.data_manager = data_manager
        
        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.timeout.connect(self.update_pomodoro)
        self.pomodoro_time_left = POMODORO_WORK_TIME
        self.is_work_time = True
        self.pomodoro_running = False
        
        self.pomodoro_player = QMediaPlayer()
        self.pomodoro_audio_output = QAudioOutput()
        self.pomodoro_player.setAudioOutput(self.pomodoro_audio_output)
        
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        sound_path = os.path.join(script_dir, "pomodoro_end.wav")
        if os.path.exists(sound_path):
            self.pomodoro_player.setSource(QUrl.fromLocalFile(sound_path))

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.editor = ZenEditor(parent_window=self)
        self.bottom_panel = self.create_bottom_panel()
        
        self.main_layout.addWidget(self.editor, 1)
        self.main_layout.addWidget(self.bottom_panel)
        
        self.editor.setPlainText(initial_text)
        self.editor.textChanged.connect(self.update_word_count)
        
        self.exit_button = QPushButton(self)
        self.exit_button.setFixedSize(32, 32)
        self.exit_button.clicked.connect(self.close)
        
        self.settings_panel = SettingsPanel(
            self.settings, 
            self.loc, 
            self, 
            context="zen_mode"
        )
        self.settings_panel.settings_changed.connect(self.data_manager.update_settings)
        self.settings_panel.hide()
        self.settings_panel.installEventFilter(self)
                
        self.audio_container = None
        self.global_audio_widget = None
        self._global_audio_controller = None
        self._overlay = None
        self._audio_overlay = None
        
        self.loc.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self.editor.setFocus()
        
        self.update_background_and_styles()
        self.apply_editor_style(self.settings)

    # ВСТАВИТЬ ВНУТРЬ КЛАССА ZenModeWindow
    def _create_themed_menu(self):
        menu = QMenu(self)
        settings = self.data_manager.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border_color = "#555" if is_dark else "#ced4da"
        
        stylesheet = f"""
            QMenu {{ background-color: {comp_bg}; color: {text}; border: 1px solid {border_color}; border-radius: 6px; padding: 5px; }}
            QMenu::item {{ padding: 6px 15px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {accent}; color: white; }}
            QMenu::separator {{ height: 1px; background-color: {border_color}; margin: 5px 10px; }}
        """
        menu.setStyleSheet(stylesheet)
        return menu

    def apply_editor_style(self, settings):
        font_family = settings.get("zen_font_family", "Georgia")
        font_size = settings.get("zen_font_size", 16)
        
        is_dark = settings.get("theme") == "dark"
        default_color = settings.get("dark_theme_text") if is_dark else settings.get("light_theme_text")
        editor_color = settings.get("zen_font_color") or default_color
        
        alignment = Qt.AlignmentFlag.AlignJustify if settings.get("zen_alignment") == "justify" else Qt.AlignmentFlag.AlignLeft
        indent = settings.get("zen_first_line_indent", 0)
        
        padding_top = settings.get("editor_padding_top", 8)
        padding_bottom = settings.get("editor_padding_bottom", 8)
        padding_left = settings.get("editor_padding_left", 10)
        padding_right = settings.get("editor_padding_right", 10)

        self.editor.setAlignment(alignment)
        
        f = self.editor.font()
        f.setFamily(font_family)
        f.setPointSize(font_size)
        self.editor.setFont(f)
        
        # Стиль для цвета и отступов
        current_style = self.editor.styleSheet()
        new_style = f"""
            color: {editor_color};
            padding-top: {padding_top}px;
            padding-bottom: {padding_bottom}px;
            padding-left: {padding_left}px;
            padding-right: {padding_right}px;
        """
        # Мы добавляем стиль, а не перезаписываем, чтобы сохранить фон
        self.editor.setStyleSheet(f"QTextEdit {{ {new_style} }}")

        cursor = self.editor.textCursor()
        block_format = cursor.blockFormat()
        block_format.setTextIndent(indent)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(block_format)
        cursor.clearSelection()
        self.editor.setTextCursor(cursor)

    def eventFilter(self, obj, event):
        # Добавляем скрытие оверлея плеера, если открыта панель настроек
        if obj is self.settings_panel and event.type() == QEvent.Type.Show:
             if self._audio_overlay and self._audio_overlay.isVisible():
                self.audio_container.hide()
                self._audio_overlay.hide()
                
        if obj is self.settings_panel and event.type() == QEvent.Type.Hide:
            if self._overlay and self._overlay.isVisible():
                self._overlay.hide()
        return super().eventFilter(obj, event)

    def toggle_settings_panel(self):
        if self.settings_panel.isVisible():
            self.settings_panel.hide()
            #if self._overlay:
            #    self._overlay.hide()
            return
            
        if not self._overlay:
            self._overlay = QWidget(self)
            self._overlay.setObjectName("zenOverlay")
            self._overlay.setStyleSheet("background: transparent;")
            self._overlay.mousePressEvent = self._overlay_clicked
            
        self._overlay.setGeometry(self.rect())
        self._overlay.show()
        
        self.settings_panel.setParent(self)
        panel_size = self.settings_panel.sizeHint()
        x = (self.width() - panel_size.width()) // 2
        y = (self.height() - panel_size.height()) // 2
        self.settings_panel.move(x, y)
        self.settings_panel.show()
        self.settings_panel.raise_()
    
    def _overlay_clicked(self, event):
        if not self.settings_panel.geometry().contains(event.pos()):
            self.settings_panel.hide()
            self._overlay.hide()
            

    def retranslate_ui(self):
        self.pomodoro_title_label.setText(f"<b>{self.loc.get('pomodoro_label')}</b>")
        self.pomodoro_start_button.setText(self.loc.get('pomodoro_start_btn') if not self.pomodoro_running else self.loc.get('pomodoro_pause_btn'))
        self.pomodoro_reset_button.setText(self.loc.get('pomodoro_reset_btn'))
        self.update_word_count()

    def create_bottom_panel(self):
        panel = QWidget()
        panel.setObjectName("bottomPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(10)

        # Контейнер для Pomodoro
        pomodoro_container = QFrame()
        pomodoro_container.setObjectName("textContainer")
        pomodoro_layout = QHBoxLayout(pomodoro_container)
        pomodoro_layout.setContentsMargins(10, 0, 10, 0)
        
        self.pomodoro_title_label = QLabel(f"<b>{self.loc.get('pomodoro_label')}</b>")
        self.pomodoro_label = QLabel("25:00")
        self.pomodoro_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomodoro_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pomodoro_layout.addWidget(self.pomodoro_title_label)
        pomodoro_layout.addWidget(self.pomodoro_label)

        # Кнопки
        self.pomodoro_start_button = QPushButton(self.loc.get('pomodoro_start_btn'))
        self.pomodoro_reset_button = QPushButton(self.loc.get('pomodoro_reset_btn'))
        self.pomodoro_start_button.clicked.connect(self.start_pause_pomodoro)
        self.pomodoro_reset_button.clicked.connect(self.reset_pomodoro)
        
        self.global_audio_btn = QPushButton()
        self.global_audio_btn.setToolTip(self.loc.get("audio_toggle_tooltip"))
        self.global_audio_btn.clicked.connect(self._toggle_global_audio_widget)

        # Контейнер для счетчика слов
        words_container = QFrame()
        words_container.setObjectName("textContainer")
        words_layout = QHBoxLayout(words_container)
        words_layout.setContentsMargins(10, 2, 10, 2)
        
        self.word_count_label = QLabel(self.loc.get('word_count_label') + ": 0")
        words_layout.addWidget(self.word_count_label)
        
        # Кнопка настроек
        self.settings_button = QPushButton(self)
        self.settings_button.clicked.connect(self.toggle_settings_panel)

        # Добавляем все в главный layout
        layout.addWidget(pomodoro_container)
        layout.addWidget(self.pomodoro_start_button)
        layout.addWidget(self.pomodoro_reset_button)
        layout.addWidget(self.global_audio_btn)
        layout.addStretch()
        layout.addWidget(words_container)
        layout.addSpacing(20)
        layout.addWidget(self.settings_button)

        ### ИЗМЕНЕНИЕ: Выравниваем высоту всех элементов ###
        QApplication.processEvents() 
        base_height = self.pomodoro_start_button.sizeHint().height()
        
        # Увеличиваем целевую высоту на 25%
        target_height = int(base_height * 1.25)

        # Применяем эту высоту к текстовым элементам и кнопкам Pomodoro
        pomodoro_container.setFixedHeight(target_height)
        self.pomodoro_start_button.setFixedHeight(target_height)
        self.pomodoro_reset_button.setFixedHeight(target_height)
        self.global_audio_btn.setFixedHeight(target_height)
        words_container.setFixedHeight(target_height)
        
        # Кнопку настроек делаем круглой и одного размера с высотой
        self.settings_button.setFixedSize(target_height, target_height)

        return panel
        
    def start_pause_pomodoro(self):
        self.pomodoro_running = not self.pomodoro_running
        self.retranslate_ui()
        if self.pomodoro_running:
            self.pomodoro_timer.start(1000)
        else:
            self.pomodoro_timer.stop()

    def reset_pomodoro(self):
        self.pomodoro_timer.stop()
        self.pomodoro_running = False
        self.is_work_time = True
        self.pomodoro_time_left = POMODORO_WORK_TIME
        self.retranslate_ui()
        self.update_pomodoro_label()

    def update_pomodoro(self):
        if not self.pomodoro_running:
            return
        self.pomodoro_time_left -= 1
        self.update_pomodoro_label()
        if self.pomodoro_time_left <= 0:
            if self.pomodoro_player.source().isValid():
                self.pomodoro_player.play()
            self.is_work_time = not self.is_work_time
            self.pomodoro_time_left = POMODORO_WORK_TIME if self.is_work_time else POMODORO_BREAK_TIME

    def update_pomodoro_label(self):
        mins, secs = divmod(self.pomodoro_time_left, 60)
        self.pomodoro_label.setText(f"{mins:02d}:{secs:02d}")

    def update_word_count(self):
        text = self.editor.toPlainText()
        cnt = len(text.split()) if text else 0
        self.word_count_label.setText(f"{self.loc.get('word_count_label')}: {cnt}")

    def attach_global_audio_widget(self, controller, loc=None):
        self._global_audio_controller = controller
        if self.audio_container is None:
            try:
                self.audio_container = QFrame(self)
                self.audio_container.setObjectName("audioWidgetContainer")
                wrapper = QVBoxLayout(self.audio_container)
                wrapper.setContentsMargins(10, 10, 10, 10)
                wrapper.setSpacing(6)
                self.global_audio_widget = GlobalAudioWidget(controller, loc or self.loc, self.audio_container)
                wrapper.addWidget(self.global_audio_widget)
                self.audio_container.hide()
            except Exception as e:
                print("attach_global_audio_widget init error:", e)
                self.audio_container = None
                return

        self.global_audio_widget.apply_theme_icons(self.settings)

    def _toggle_global_audio_widget(self):
        if self.audio_container is None:
            if self._global_audio_controller is None:
                return
            self.attach_global_audio_widget(self._global_audio_controller, self.loc)
            if self.audio_container is None:
                return
        
        if self.audio_container.isVisible():
            self.audio_container.hide()
            if self._audio_overlay:
                self._audio_overlay.hide()
        else:
            # Создаем и показываем оверлей для плеера
            if not self._audio_overlay:
                self._audio_overlay = QWidget(self)
                self._audio_overlay.setObjectName("audioOverlay")
                self._audio_overlay.setStyleSheet("background: transparent;")
                self._audio_overlay.mousePressEvent = self._audio_overlay_clicked
            
            self._audio_overlay.setGeometry(self.rect())
            self._audio_overlay.show()
            
            self.audio_container.setParent(self) # Убеждаемся, что родитель - окно
            self.audio_container.adjustSize()
            width = max(360, self.audio_container.width())
            self.audio_container.setFixedWidth(width)
            x = (self.width() - self.audio_container.width()) // 2
            y = (self.height() - self.audio_container.height()) // 2
            self.audio_container.move(max(0, x), max(0, y))
            self.audio_container.show()
            self.audio_container.raise_()

    def _audio_overlay_clicked(self, event):
        # Закрываем плеер и оверлей, если клик был не по плееру
        if not self.audio_container.geometry().contains(event.pos()):
            self.audio_container.hide()
            self._audio_overlay.hide()

    def _update_styles(self):
        is_dark, accent, _, _, _ = theme_colors(self.settings)
        hp = self.width() * self.settings.get("zen_padding_horiz", 20) // 100
        vp = self.height() * self.settings.get("zen_padding_vert", 5) // 100
        self.main_layout.setContentsMargins(hp, vp, hp, vp)
        
        is_transparent = self.settings.get("zen_editor_transparent", False)
        
        bg_key = "dark_theme_bg" if is_dark else "light_theme_bg"
        editor_bg_str = self.settings.get(bg_key)
        editor_bg = QColor(editor_bg_str)
        is_transparent = self.settings.get("zen_editor_opacity", 85) < 100
        opacity_level = self.settings.get("zen_editor_opacity", 85)
        
        bg_key = "dark_theme_bg" if is_dark else "light_theme_bg"
        editor_bg_str = self.settings.get(bg_key)
        editor_bg = QColor(editor_bg_str)
        # Применяем прозрачность из настроек
        editor_bg.setAlpha(int(opacity_level / 100 * 255))
            
        default_editor_color = self.settings.get("dark_theme_text") if is_dark else self.settings.get("light_theme_text")
        editor_color = self.settings.get("zen_font_color") or default_editor_color
        alignment = Qt.AlignmentFlag.AlignJustify if self.settings.get("zen_alignment") == "justify" else Qt.AlignmentFlag.AlignLeft
        self.editor.setAlignment(alignment)
        indent = self.settings.get("zen_first_line_indent", 0)
        
        editor_bg_rgba = f"rgba({editor_bg.red()},{editor_bg.green()},{editor_bg.blue()},{editor_bg.alphaF()})"
        floating_fg = self.settings.get("dark_theme_text", "#e0e0e0") if is_dark else self.settings.get("light_theme_text", "#212529")
        component_bg = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.05)"
        hover_bg = "rgba(255,255,255,0.2)" if is_dark else "rgba(0,0,0,0.1)"
        border_color = "rgba(255,255,255,0.2)" if is_dark else "rgba(0,0,0,0.15)"
        
        if self._overlay:
            self._overlay.setStyleSheet("background: transparent")

        


        stylesheet = f"""
            QTextEdit {{
                background-color: {editor_bg_rgba}; border: none; font-family: '{self.settings.get('zen_font_family')}';
                font-size: {self.settings.get('zen_font_size')}pt; color: {editor_color};
            }}
            QWidget#bottomPanel {{
                background-color: transparent; border-top: 1px solid {border_color};
            }}
            /* Стиль для контейнеров текста */
            QFrame#textContainer {{
                color: {floating_fg}; background-color: {component_bg};
                border: 1px solid {border_color}; padding: 5px 10px; border-radius: 4px;
            }}
            QWidget#bottomPanel QLabel {{ color: {floating_fg}; background-color: transparent; }}
            QWidget#bottomPanel QPushButton {{
                color: {floating_fg}; background-color: {component_bg};
                border: 1px solid {border_color}; padding: 5px 10px; border-radius: 4px;
            }}
            QWidget#bottomPanel QPushButton:hover {{ background-color: {hover_bg}; }}
            QFrame#audioWidgetContainer {{
                background-color: {"rgba(30,30,30,0.8)" if is_dark else "rgba(248,249,250,0.85)"};
                border: 1px solid {border_color}; border-radius: 8px;
            }}
        """
        self.setStyleSheet(self.styleSheet() + stylesheet)
        
        if self.global_audio_widget:
            self.global_audio_widget.apply_zen_style(
                floating_fg=floating_fg,
                component_bg=component_bg,
                hover_bg=hover_bg,
                border_color=border_color
            )

        cursor = self.editor.textCursor()
        bf = cursor.blockFormat()
        bf.setTextIndent(indent)
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(bf)
        cursor.clearSelection()
        self.editor.setTextCursor(cursor)
        
        button_bg = "rgba(30,30,30,0.5)" if is_dark else "rgba(240,240,240,0.7)"
        self.settings_button.setStyleSheet(f"background:{button_bg}; border-radius:16px;")
        self.exit_button.setStyleSheet(f"QPushButton{{background:{button_bg}; border-radius:16px; border:none;}} QPushButton:hover{{background-color:#dc3545;}}")
        self.settings_button.setIcon(ThemedIconProvider.icon("gear", self.settings, QSize(18, 18)))
        self.exit_button.setIcon(ThemedIconProvider.icon("close", self.settings, QSize(18, 18)))
        self.global_audio_btn.setIcon(ThemedIconProvider.icon("note", self.settings, QSize(18, 18)))
        
        if self.global_audio_widget:
            self.global_audio_widget.apply_theme_icons(self.settings)

    def update_background_and_styles(self):
        is_dark = self.settings.get("theme") == "dark"
        
        bg_path = self.settings.get("zen_bg_path")
        if bg_path and os.path.exists(bg_path):
            safe_path = bg_path.replace('\\', '/')
            self.setStyleSheet(f"QWidget#ZenModeWindow {{ background-image: url({safe_path}); background-position: center; background-repeat: no-repeat; background-attachment: fixed; }}")
        else:
            bg_key = "zen_dark_theme_bg" if is_dark else "zen_light_theme_bg"
            bg_color = self.settings.get(bg_key, "#1c1c1c" if is_dark else "#e9ecef")
            self.setStyleSheet(f"QWidget#ZenModeWindow {{ background-color: {bg_color}; }}")

        self._update_styles()
        self.update()

    def update_zen_settings(self, new_settings):
        self.settings = new_settings
        self.update_background_and_styles()
        self.apply_editor_style(self.settings)
        
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)

    def resizeEvent(self, event):
        if hasattr(self, "exit_button") and self.exit_button:
            self.exit_button.move(self.width() - self.exit_button.width() - 20, 20)
        if self.audio_container and self.audio_container.isVisible():
            self.audio_container.adjustSize()
            x = (self.width() - self.audio_container.width()) // 2
            y = (self.height() - self.audio_container.height()) // 2
            self.audio_container.move(max(0, x), max(0, y))
        if self._overlay and self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())
            panel_size = self.settings_panel.sizeHint()
            x = (self.width() - panel_size.width()) // 2
            y = (self.height() - panel_size.height()) // 2
            self.settings_panel.move(x, y)
        super().resizeEvent(event)

    def showEvent(self, event):
        self.update_background_and_styles()
        super().showEvent(event)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            self.close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.blockSignals(True)
            self.zen_saved_and_closed.emit(self.editor.toPlainText())
        else:
            super().keyPressEvent(event)
        
    def closeEvent(self, event):
        self.pomodoro_timer.stop()
        self.pomodoro_running = False
        if self.settings_panel.isVisible():
            self.settings_panel.hide()
        if not self.signalsBlocked():
            self.zen_exited.emit(self.editor.toPlainText())
        event.accept()

class MainPopup(QWidget):
    animation_finished_and_hidden = pyqtSignal()

    def __init__(self, data_manager):
        super().__init__()
        self.setObjectName("MainPopup")
        self._is_closing = False
        self.data_manager = data_manager
        self.loc = data_manager.loc_manager
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedWidth(380)
        self._overlay = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 5)
        main_layout.setSpacing(6)
        
        title_bar_layout = QHBoxLayout()
        title_bar_layout.setSpacing(6)
        self.title_label = QLabel("Ассистент")
        self.title_label.setObjectName("titleLabel")

        self.audio_toggle_btn = QPushButton()
        self.audio_toggle_btn.setFixedSize(36, 28)
        self.audio_toggle_btn.clicked.connect(self._toggle_audio_view)

        self.settings_toggle_btn = QPushButton()
        self.settings_toggle_btn.setFixedSize(40, 28)
        self.settings_toggle_btn.clicked.connect(self._toggle_settings_panel_main)

        self.close_button = QPushButton()
        self.close_button.setFixedSize(28, 28)
        self.close_button.setObjectName("close_button")
        self.close_button.clicked.connect(self.close)

        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.audio_toggle_btn)
        title_bar_layout.addWidget(self.settings_toggle_btn)
        title_bar_layout.addWidget(self.close_button)
        main_layout.addLayout(title_bar_layout)
        
        top_wrap = QWidget()
        top_v = QVBoxLayout(top_wrap)
        top_v.setContentsMargins(0, 0, 0, 0)
        top_v.setSpacing(4)
        
        self.tasks_panel = TasksPanel(data_manager, parent=self)
        
        self.audio_widget_container = QFrame()
        self.audio_widget_container.setObjectName("audioWidgetContainer")
        audio_layout = QVBoxLayout(self.audio_widget_container)
        audio_layout.setContentsMargins(8,8,8,8)
        self.audio_widget = GlobalAudioWidget(self.data_manager.global_audio, self.loc, self)
        audio_layout.addWidget(self.audio_widget)
        
        self.tasks_audio_stack = QStackedWidget()
        self.tasks_audio_stack.addWidget(self.tasks_panel)
        self.tasks_audio_stack.addWidget(self.audio_widget_container)
        top_v.addWidget(self.tasks_audio_stack)
        
        self.notes_panel = NotesPanel(data_manager, parent=self)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(top_wrap)
        self.splitter.addWidget(self.notes_panel)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 6)
        main_layout.addWidget(self.splitter)
        
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.status_label)
        
        self.settings_panel_main = SettingsPanel(
            self.data_manager.get_settings(), 
            self.loc, 
            self, 
            context="main_popup"
        )
        self.settings_panel_main.settings_changed.connect(self.data_manager.update_settings)
        self.settings_panel_main.hide()
        self.settings_panel_main.installEventFilter(self)
        
        self._setup_shortcuts()
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation_group = QParallelAnimationGroup(self)
        self.animation_group.addAnimation(self.pos_animation)
        self.animation_group.addAnimation(self.opacity_animation)
        self.animation_group.finished.connect(self.on_animation_finished)
        self.set_status_saved()
        self.notes_panel.zen_mode_requested.connect(data_manager.enter_zen_mode)
        self.apply_theme(self.data_manager.get_settings())

    def _create_themed_menu(self):
        menu = QMenu(self)
        settings = self.data_manager.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border_color = "#555" if is_dark else "#ced4da"
        
        stylesheet = f"""
            QMenu {{ background-color: {comp_bg}; color: {text}; border: 1px solid {border_color}; border-radius: 6px; padding: 5px; }}
            QMenu::item {{ padding: 6px 15px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {accent}; color: white; }}
            QMenu::separator {{ height: 1px; background-color: {border_color}; margin: 5px 10px; }}
        """
        menu.setStyleSheet(stylesheet)
        return menu

    def eventFilter(self, obj, event):
        if obj is self.settings_panel_main and event.type() == QEvent.Type.Hide:
            if self._overlay and self._overlay.isVisible():
                self._overlay.hide()
        return super().eventFilter(obj, event)

    def _toggle_audio_view(self):
        self.tasks_audio_stack.setCurrentIndex(1 if self.tasks_audio_stack.currentIndex() == 0 else 0)

    def _toggle_settings_panel_main(self):
        if self.settings_panel_main.isVisible():
            self.settings_panel_main.hide()
            return

        if not self._overlay:
            self._overlay = QWidget(self.nativeParentWidget())
            self._overlay.setObjectName("settingsOverlay")
            self._overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self._overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._overlay.setStyleSheet("background: transparent;")
            self._overlay.mousePressEvent = self._overlay_clicked

        screen_rect = self.screen().geometry()
        self._overlay.setGeometry(screen_rect)
        self._overlay.show()

        self.settings_panel_main.setParent(self._overlay)
        panel_size = self.settings_panel_main.sizeHint()
        x = screen_rect.x() + (screen_rect.width() - panel_size.width()) // 2
        y = screen_rect.y() + (screen_rect.height() - panel_size.height()) // 2
        self.settings_panel_main.move(x, y)
        self.settings_panel_main.show()
        self.settings_panel_main.raise_()

    def _overlay_clicked(self, event):
        # Конвертируем глобальные координаты клика в локальные для панели
        mapped_pos = self.settings_panel_main.mapFromGlobal(event.globalPosition().toPoint())
        # Закрываем, только если клик был не по панели настроек
        if not self.settings_panel_main.rect().contains(mapped_pos):
            self.settings_panel_main.hide()
            self._overlay.hide()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self, activated=self._audio_toggle_play_pause)
        QShortcut(QKeySequence("Delete"), self, activated=self._audio_remove_selected)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._audio_add_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self._audio_add_folder)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=self._audio_prev)
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=self._audio_next)
        QShortcut(QKeySequence("M"), self, activated=lambda: self.audio_widget._toggle_mute())

    def _is_player_active(self):
        return hasattr(self, "tasks_audio_stack") and self.tasks_audio_stack.currentIndex() == 1

    def _audio_toggle_play_pause(self):
        if self._is_player_active(): self.data_manager.global_audio.toggle_play_pause()
    def _audio_prev(self):
        if self._is_player_active(): self.data_manager.global_audio.prev()
    def _audio_next(self):
        if self._is_player_active(): self.data_manager.global_audio.next()
    def _audio_add_files(self):
        if self._is_player_active(): self.audio_widget._add_files()
    def _audio_add_folder(self):
        if self._is_player_active(): self.audio_widget._add_folder()
    def _audio_remove_selected(self):
        if self._is_player_active(): self.audio_widget._remove_selected()

    def retranslate_ui(self):
        self.tasks_panel.retranslate_ui()
        self.notes_panel.retranslate_ui()
        
        self.audio_toggle_btn.setToolTip(self.loc.get("audio_toggle_tooltip"))
        self.settings_toggle_btn.setToolTip(self.loc.get("settings_title"))
        self.on_data_changed()
        self.set_status_saved()

    def apply_theme(self, settings):
        is_dark, accent, bg, text, list_text = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        panel_bg = QColor(comp_bg).lighter(108).name() if is_dark else QColor(comp_bg).lighter(103).name()
        border = "#555" if is_dark else "#ced4da"
        qtool_hover = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.06)"
        
        stylesheet = f"""
            QWidget#MainPopup {{ background-color:{bg}; }}
            QWidget#settingsOverlay {{ background: rgba(0,0,0,0.5); }}
            QWidget, QLabel {{ color:{text}; background-color:transparent; }}
            QFrame#audioWidgetContainer {{ background-color:{panel_bg}; border:1px solid {border}; border-radius:8px; }}
            QLabel#titleLabel{{font-size:14px;font-weight:bold;}}
            
            QLineEdit, QTextEdit, QComboBox {{
                background-color:{comp_bg}; border:1px solid {border};
                border-radius:6px; padding:6px;
            }}
            QComboBox QAbstractItemView{{
                background-color:{comp_bg}; color:{text}; border:1px solid {border};
                selection-background-color:{accent}; selection-color:white; outline:0px;
            }}
            
            QListWidget{{ background-color:{comp_bg}; border:1px solid {border}; border-radius:6px; }} 
            QListWidget:focus{{ outline:none; }}
            QListWidget::item{{ color:{list_text}; padding:6px; border-radius:4px; }}
            QListWidget::item:hover{{ background-color:rgba(128,128,128,0.15); }}
            QListWidget#TaskList::item:selected{{ background-color:transparent; color:{list_text}; }}
            QListWidget::item:selected{{ background-color:{accent}; color:white; }}
            
            QCheckBox{{ spacing:8px; color:{text}; }}
            QCheckBox::indicator{{
                width:16px; height:16px; border:2px solid {'#888' if is_dark else '#adb5bd'};
                border-radius:3px; background:{'#2d2d2d' if is_dark else '#ffffff'};
            }}
            QCheckBox::indicator:hover{{ border-color:{accent}; }}
            QCheckBox::indicator:checked{{ border-color:{accent}; background:{accent}; }}
            
            QListWidget#TaskList::indicator {{
                width: 16px; height: 16px;
                border: 2px solid {'#888' if is_dark else '#adb5bd'};
                border-radius: 3px; background: transparent;
            }}
            QListWidget#TaskList::indicator:hover {{ border-color: {accent}; }}
            QListWidget#TaskList::indicator:checked {{ background-color: {accent}; border-color: {accent}; }}

            QPushButton {{
                background-color:{comp_bg}; color:{text}; border:1px solid {border};
                border-radius:4px; padding: 5px 10px;
            }}
            QPushButton:hover {{ background-color: {qtool_hover}; }}
            QPushButton#close_button, QPushButton#window_button, QPushButton#settings_toggle_btn, QPushButton#audio_toggle_btn {{
                background-color:transparent; border:none;
            }}
            
            QSplitter::handle {{ background-color:transparent; }}
            QSplitter::handle:hover {{ background-color:rgba(128,128,128,0.15); }}
            QSlider::groove:horizontal{{ background:transparent; height:4px; }}
            QSlider::handle:horizontal{{ background:{accent}; width:12px; margin:-2px; border-radius:3px; }}
            QSlider::sub-page:horizontal{{ background:{accent}; }}
        """
        self.setStyleSheet(stylesheet)
        
        self.audio_toggle_btn.setIcon(ThemedIconProvider.icon("note", settings, QSize(18, 18)))
        self.settings_toggle_btn.setIcon(ThemedIconProvider.icon("gear", settings, QSize(18, 18)))
        #self.window_button.setIcon(ThemedIconProvider.icon("window", settings, QSize(18, 18)))
        self.close_button.setIcon(ThemedIconProvider.icon("close", settings, QSize(18, 18)))
        self.notes_panel.window_button.setIcon(ThemedIconProvider.icon("window", settings))
        
        if hasattr(self, "audio_widget"):
            self.audio_widget.apply_theme_icons(settings)
        for i in range(self.tasks_panel.task_list_widget.count()):
            self.tasks_panel.update_task_item_style(self.tasks_panel.task_list_widget.item(i))
        if hasattr(self, "settings_panel_main"):
            self.settings_panel_main.apply_styles()

    def on_data_changed(self):
        self.status_label.setText(self.loc.get("unsaved_changes_status"))
        self.status_label.setStyleSheet("color:#dc3545;font-size:10px;margin-right:5px;")

    def set_status_saved(self):
        self.status_label.setText(self.loc.get("data_saved_status"))
        self.status_label.setStyleSheet("color:#28a745;font-size:10px;margin-right:5px;")

    def show_animated(self, position, from_left=False):
        if self.isVisible(): return
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(position.x(), screen_geo.y(), 380, screen_geo.height())
        start_pos = QPoint(-self.width(), self.y()) if from_left else QPoint(screen_geo.width(), self.y())
        self.pos_animation.setDuration(300)
        self.pos_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.pos_animation.setStartValue(start_pos)
        self.pos_animation.setEndValue(self.pos())
        self.opacity_animation.setDuration(250)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.setWindowOpacity(0.0)
        self.move(start_pos)
        self.show()
        self.animation_group.start()

    def hide_animated(self, to_left=False):
        if not self.isVisible() or self._is_closing: return
        self._is_closing = True
        end_x = -self.width() if to_left else self.screen().geometry().width()
        end_pos = QPoint(end_x, self.y())
        self.pos_animation.setStartValue(self.pos())
        self.pos_animation.setEndValue(end_pos)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.animation_group.start()

    def on_animation_finished(self):
        if self.windowOpacity() < 0.1:
            self.hide()
            self._is_closing = False
            self.animation_finished_and_hidden.emit()

    def close(self):
        self.hide_animated(to_left=self.data_manager.settings.get("trigger_pos") == "left")

    def resizeEvent(self, event):
        if self._overlay and self._overlay.isVisible():
            self._overlay.resize(self.size())
            x = (self.width() - self.settings_panel_main.width()) // 2
            y = (self.height() - self.settings_panel_main.height()) // 2
            self.settings_panel_main.move(max(0, x), max(0, y))
        super().resizeEvent(event)


class NotesTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setObjectName("NotesTree")
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)

    def _is_folder(self, item):
        if not item:
            return False
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        return nd.get("type") == "folder"

    def dragMoveEvent(self, event):
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        drop_indicator_pos = self.dropIndicatorPosition()

        if drop_indicator_pos == QAbstractItemView.DropIndicatorPosition.OnItem:
            if not self._is_folder(item):
                event.ignore()
                return
        event.accept()


class NotesTreeSidebar(QWidget):
    folder_selected = pyqtSignal(QTreeWidgetItem)
    note_selected = pyqtSignal(QTreeWidgetItem)
    selection_cleared = pyqtSignal()
    note_deleted_from_tree = pyqtSignal(str) 
    
    def __init__(self, notes_panel: NotesPanel, loc_manager: LocalizationManager, main_window: 'WindowMain', parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.loc = loc_manager
        self.notes_panel = notes_panel
        self.pending_target_folder = None
        self._building = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tree = NotesTreeWidget(self)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._open_context_menu)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree, 1)
        
        model = self.tree.model()
        model.rowsMoved.connect(lambda *a: self._save())
        model.rowsInserted.connect(lambda *a: self._save())
        model.rowsRemoved.connect(lambda *a: self._save())

    def set_model(self, tree_list):
        self._building = True
        try:
            self.tree.model().blockSignals(True)
            self.tree.clear()
            root = self.tree.invisibleRootItem()
            if tree_list:
                for node in tree_list:
                    self._append_node(root, node)
            self.tree.expandAll()
        finally:
            self.tree.model().blockSignals(False)
            self._building = False
        self.refresh_aliases()

    def get_model(self):
        def build(parent_item):
            out = []
            for i in range(parent_item.childCount()):
                it = parent_item.child(i)
                nd = it.data(0, Qt.ItemDataRole.UserRole) or {}
                if nd.get("type") == "folder":
                    out.append({"type": "folder", "name": nd.get("name", ""), "children": build(it)})
                else:
                    out.append({"type": "note", "timestamp": nd.get("timestamp", "")})
            return out
        return build(self.tree.invisibleRootItem())

    def _get_note_alias_from_cache(self, timestamp):
        """Находит текст заметки в кеше и возвращает первую строку."""
        all_notes = self.notes_panel.data_manager.get_all_notes_from_cache()
        for note in all_notes:
            if note.get("timestamp") == timestamp:
                text = note.get("text", "").strip()
                alias = text.split('\n', 1)[0].strip() if text else timestamp
                return alias[:30] if len(alias) > 30 else alias
        return timestamp # Если заметка не найдена

    def _append_node(self, parent_item, node_data):
        node_type = node_data.get("type")
        settings = self.notes_panel.data_manager.get_settings()
        if node_type == "folder":
            item = QTreeWidgetItem(parent_item, [node_data.get("name", "Folder")])
            item.setIcon(0, ThemedIconProvider.icon("folder", settings))
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": node_data.get("name", "")})
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)
            if "children" in node_data:
                for child_node in node_data["children"]:
                    self._append_node(item, child_node)
        elif node_type == "note":
            ts = node_data.get("timestamp", "")
            # ИЗМЕНЕНИЕ: Сразу устанавливаем правильное имя
            alias = self._get_note_alias_from_cache(ts)
            item = QTreeWidgetItem(parent_item, [alias])
            item.setIcon(0, ThemedIconProvider.icon("file", settings))
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "note", "timestamp": ts})
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsDragEnabled)

    def refresh_aliases(self):
        # Этот метод теперь обновляет иконки (закреплена/не закреплена)
        ts_map = {}
        all_notes = self.notes_panel.data_manager.get_all_notes_from_cache()
        for note in all_notes:
            ts = note.get("timestamp", "")
            if ts:
                text = note.get("text", "")
                pinned = note.get("pinned", False)
                alias = (text.strip().splitlines()[0] if text else "").strip()
                if not alias:
                    alias = ts
                ts_map[ts] = (alias[:30], pinned) 
        
        settings = self.notes_panel.data_manager.get_settings()
        pin_icon = ThemedIconProvider.icon("pin", settings)
        file_icon = ThemedIconProvider.icon("file", settings)
        
        def apply(parent_item):
                for i in range(parent_item.childCount()):
                    ch = parent_item.child(i)
                    md = ch.data(0, Qt.ItemDataRole.UserRole) or {}
                    if md.get("type") == "note":
                        ts = md.get("timestamp", "")
                        if ts and ts in ts_map:
                            alias, pinned = ts_map[ts]
                            ch.setText(0, alias)
                            ch.setIcon(0, pin_icon if pinned else file_icon)
                    else:
                        ch.setIcon(0, ThemedIconProvider.icon("folder", settings))
                        apply(ch)
        apply(self.tree.invisibleRootItem())

    def _create_themed_menu(self):
        if self.main_window and hasattr(self.main_window, '_create_themed_menu'):
            return self.main_window._create_themed_menu()
        return QMenu(self)

    def _open_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = self._create_themed_menu()
        if item:
            nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if nd.get("type") == "folder":
                menu.addAction(self.loc.get("tree_new_note_here"), lambda: self._new_note_here(item))
                menu.addSeparator()
                menu.addAction(self.loc.get("tree_new_folder"), lambda: self._create_folder(item))
                menu.addAction(self.loc.get("tree_rename_folder"), lambda: self._rename_folder(item))
                menu.addAction(self.loc.get("tree_delete_folder"), lambda: self._delete_folder(item))
            else:
                menu.addAction(self.loc.get("tree_delete_note"), lambda: self._delete_note(item))
                menu.addSeparator()
                menu.addAction("Поднять на уровень выше", lambda: self._move_item_up(item))
                menu.addAction("В корень", lambda: self._move_item_to_root(item))
        else:
            root = self.tree.invisibleRootItem()
            menu.addAction(self.loc.get("tree_new_note_here"), lambda: self._new_note_here(root))
            menu.addSeparator()
            menu.addAction(self.loc.get("tree_new_folder"), lambda: self._create_folder(root))
        menu.exec(self.tree.viewport().mapToGlobal(pos))
        
    def _move_item_up(self, item):
        if not item or not item.parent(): return
        current_parent = item.parent()
        new_parent = current_parent.parent() or self.tree.invisibleRootItem()
        new_parent.addChild(current_parent.takeChild(current_parent.indexOfChild(item)))
        self._save()

    def _move_item_to_root(self, item):
        if not item or not item.parent(): return
        root = self.tree.invisibleRootItem()
        current_parent = item.parent()
        root.addChild(current_parent.takeChild(current_parent.indexOfChild(item)))
        self._save()

    def _new_note_here(self, folder_item):
        if not self.main_window: return
        self.main_window.save_current_item()
        self.pending_target_folder = folder_item or self.tree.invisibleRootItem()
        self.notes_panel.clear_for_new_note(force=True)
        self.main_window.current_edit_target = None
        self.main_window.editor_context_label.setText(f"<b>{self.loc.get('new_note_title', 'Новая заметка')}</b>")

    def clear_pending_folder(self):
        self.pending_target_folder = None

    def _create_folder(self, parent_item):
        name, ok = QInputDialog.getText(self, self.loc.get("tree_new_folder"), self.loc.get("tree_new_folder"))
        if not ok or not name.strip(): return
        node = {"type": "folder", "name": name.strip(), "children": []}
        self._append_node(parent_item, node)
        if parent_item != self.tree.invisibleRootItem(): self.tree.expandItem(parent_item)
        self._save()

    def _rename_folder(self, item):
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        old = nd.get("name", "")
        name, ok = QInputDialog.getText(self, self.loc.get("tree_rename_folder"), self.loc.get("tree_rename_folder"), QLineEdit.EchoMode.Normal, old)
        if not ok or not name.strip(): return
        nd["name"] = name.strip()
        item.setData(0, Qt.ItemDataRole.UserRole, nd)
        item.setText(0, name.strip())
        self._save()

    def _delete_folder(self, item):
        if not item: return
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        name = nd.get("name", "")
        reply = QMessageBox.question(self, self.loc.get("tree_delete_folder"), self.loc.get("tree_confirm_delete_folder").format(name=name))
        if reply != QMessageBox.StandardButton.Yes: return
        while item.childCount() > 0:
            child = item.child(0)
            if self.tree._is_folder(child): self._delete_folder(child)
            else: self._delete_note(child)
        parent = item.parent() or self.tree.invisibleRootItem()
        parent.removeChild(item)
        self._save()

    def _delete_note(self, item):
        if not item: return
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        ts = nd.get("timestamp")
        if not ts: return
        parent = item.parent() or self.tree.invisibleRootItem()
        parent.removeChild(item)
        self.note_deleted_from_tree.emit(ts)
        self.notes_panel.data_manager.delete_note_by_timestamp_from_all_data(ts)

    def _find_note_item(self, timestamp: str, parent_item=None):
        if not timestamp: return None
        if parent_item is None: parent_item = self.tree.invisibleRootItem()
        for i in range(parent_item.childCount()):
            it = parent_item.child(i)
            nd = it.data(0, Qt.ItemDataRole.UserRole) or {}
            if nd.get("type") == "note" and nd.get("timestamp") == timestamp: return it
            if nd.get("type") == "folder":
                if f := self._find_note_item(timestamp, it): return f
        return None

    def _on_selection_changed(self):
        if self._building: return
        items = self.tree.selectedItems()
        if not items:
            self.selection_cleared.emit()
            return
        it = items[0]
        nd = it.data(0, Qt.ItemDataRole.UserRole) or {}
        if nd.get("type") == "note": self.note_selected.emit(it)
        elif nd.get("type") == "folder": self.folder_selected.emit(it)

    def apply_visibility(self, visible_timestamps: set):
        def is_visible_recursive(item):
            nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if nd.get("type") == "note":
                is_vis = nd.get("timestamp") in visible_timestamps
                item.setHidden(not is_vis)
                return is_vis
            any_child_visible = False
            for i in range(item.childCount()):
                if is_visible_recursive(item.child(i)):
                    any_child_visible = True
            item.setHidden(not any_child_visible)
            return any_child_visible
        is_visible_recursive(self.tree.invisibleRootItem())
    
    def on_note_created(self, timestamp: str):
        if self._building or not timestamp: return
        parent_item = self.pending_target_folder or self.tree.invisibleRootItem()
        self.clear_pending_folder()
        if self._find_note_item(timestamp):
            self.refresh_aliases()
            return
        self._append_node(parent_item, {"type": "note", "timestamp": timestamp})
        self.tree.expandItem(parent_item)
        if new_item := self._find_note_item(timestamp, parent_item):
            self.tree.setCurrentItem(new_item)
        self.refresh_aliases()

    def on_note_deleted(self, timestamp: str):
        if self._building or not timestamp: return
        if item_to_delete := self._find_note_item(timestamp):
            parent = item_to_delete.parent() or self.tree.invisibleRootItem()
            parent.removeChild(item_to_delete)

    def _save(self):
        if self._building: return
        try: self.notes_panel.data_manager.save_app_data()
        except Exception as e: print(f"NotesTreeSidebar._save error: {e}")

class WindowMain(QWidget):
    window_closed = pyqtSignal()
    splitter_sizes_changed = pyqtSignal(list)

    def __init__(self, data_manager):
        super().__init__()
        self.setObjectName("MainWindow")
        self.data_manager = data_manager
        self.loc = data_manager.loc_manager
        self._overlay = None
        self.current_edit_target = None
        self._is_resizing = False
        self.setWindowTitle(self.loc.get("app_title", "Ассистент 2.0"))
        
        min_left = self.data_manager.get_settings().get("window_min_width_left", 260)
        min_right = self.data_manager.get_settings().get("window_min_width_right", 380)
        self.setMinimumSize(min_left + min_right + 260, 700)
        self.resize(1200, 860)
        
        self.splitter_save_timer = QTimer(self)
        self.splitter_save_timer.setSingleShot(True)
        self.splitter_save_timer.setInterval(500)
        self.splitter_save_timer.timeout.connect(self._save_splitter_sizes)
        
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(250)
        self.resize_timer.timeout.connect(self._on_resize_finished)

        self.window_editor_font_size = self.data_manager.get_settings().get("window_editor_font_size", 0)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 10)
        main_layout.setSpacing(10)
        title_bar_layout = QHBoxLayout()
        title_bar_layout.setSpacing(8)
        self.title_label = QLabel("Ассистент")
        self.title_label.setObjectName("titleLabel")
        self.left_toggle = QToolButton()
        self.left_toggle.setCheckable(True)
        self.right_toggle = QToolButton()
        self.right_toggle.setCheckable(True)
        self.audio_toggle_btn = QToolButton()
        self.audio_toggle_btn.clicked.connect(self._toggle_audio_view)
        self.settings_toggle_btn = QToolButton()
        self.settings_toggle_btn.clicked.connect(self._toggle_settings_panel_main)
        self.to_panel_button = QPushButton()
        self.to_panel_button.setObjectName("toPanelButton")
        self.to_panel_button.clicked.connect(self.data_manager.switch_to_popup_from_window)
        self.close_button = QToolButton()
        self.close_button.setObjectName("windowCloseButton")
        self.close_button.clicked.connect(self.close)
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.left_toggle)
        title_bar_layout.addWidget(self.right_toggle)
        title_bar_layout.addSpacing(10)
        title_bar_layout.addWidget(self.audio_toggle_btn)
        title_bar_layout.addWidget(self.settings_toggle_btn)
        title_bar_layout.addWidget(self.to_panel_button)
        title_bar_layout.addWidget(self.close_button)
        main_layout.addLayout(title_bar_layout)
        
        self.tasks_panel = TasksPanel(data_manager, self)
        self.notes_panel = NotesPanel(data_manager, self)

        self.notes_panel.zen_mode_requested.connect(self.data_manager.enter_zen_mode)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(12)
        self.splitter.setOpaqueResize(False)
        self.splitter.splitterMoved.connect(self._save_splitter_sizes)
        self.splitter.splitterMoved.connect(self.splitter_save_timer.start)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        self.splitter.setChildrenCollapsible(False)
        self.left_container = QWidget()
        self.left_container.setObjectName("cardContainer")
        self.left_container.setMinimumWidth(min_left)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(6)
        lf = QHBoxLayout()
        lf.setContentsMargins(0, 0, 0, 0)
        lf.addWidget(self.notes_panel.search_input, 1)
        lf.addWidget(self.notes_panel.tag_filter_combo)
        left_layout.addLayout(lf)
        self.tree_sidebar = NotesTreeSidebar(self.notes_panel, self.loc, self, self)
        left_layout.addWidget(self.tree_sidebar, 1)
        self.notes_panel.note_list_widget.hide()
        self.center_container = QWidget()
        self.center_container.setObjectName("cardContainer")
        self.center_container.setMinimumWidth(260)
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_layout.setSpacing(6)
        self.editor_context_label = QLabel()
        self.editor_context_label.setObjectName("contextLabel")
        center_layout.addWidget(self.editor_context_label)
        editor_toolbar = QHBoxLayout()
        editor_toolbar.setSpacing(6)
        editor_toolbar.addWidget(self.notes_panel.new_button)
        editor_toolbar.addWidget(self.notes_panel.zen_button)
        self.to_task_btn = QPushButton()
        self.to_task_btn.clicked.connect(self._add_selection_as_task)
        editor_toolbar.addWidget(self.to_task_btn)
        editor_toolbar.addStretch()
        editor_toolbar.addWidget(self.notes_panel.save_button)
        center_layout.addLayout(editor_toolbar)
        self.chips_scroll = QScrollArea()
        self.chips_scroll.setObjectName("chipsScroll")
        self.chips_scroll.setWidgetResizable(True)
        self.chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chips_host = QWidget()
        chips_host.setObjectName("chipsHost")
        self.chips_layout = QHBoxLayout(chips_host)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(6)
        self.chips_scroll.setWidget(chips_host)
        center_layout.addWidget(self.chips_scroll)
        center_layout.addWidget(self.notes_panel.notes_editor, 1)
        self.right_container = QWidget()
        self.right_container.setObjectName("cardContainer")
        self.right_container.setMinimumWidth(min_right)
        right_v = QVBoxLayout(self.right_container)
        right_v.setContentsMargins(10, 10, 10, 10)
        right_v.setSpacing(6)
        self.audio_widget_container = QFrame()
        self.audio_widget_container.setObjectName("audioWidgetContainer")
        audio_layout = QVBoxLayout(self.audio_widget_container)
        audio_layout.setContentsMargins(8,8,8,8)
        self.audio_widget = GlobalAudioWidget(self.data_manager.global_audio, self.loc, self)
        audio_layout.addWidget(self.audio_widget)
        self.right_stack = QStackedWidget()
        self.right_stack.addWidget(self.tasks_panel)
        self.right_stack.addWidget(self.audio_widget_container)
        right_v.addWidget(self.right_stack, 1)
        self.splitter.addWidget(self.left_container)
        self.splitter.addWidget(self.center_container)
        self.splitter.addWidget(self.right_container)
        main_layout.addWidget(self.splitter, 1)
        self.resize_overlay = QFrame(self.splitter)
        self.resize_overlay.setObjectName("resizeOverlay")
        overlay_layout = QVBoxLayout(self.resize_overlay)
        overlay_label = QLabel("Пересчет макета...")
        overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(overlay_label)
        self.resize_overlay.hide()
        self.status_bar = QStatusBar()
        self.status_text = QLabel("")
        self.word_count_label = QLabel("")
        self.status_bar.addWidget(self.status_text, 1)
        self.status_bar.addPermanentWidget(self.word_count_label)
        main_layout.addWidget(self.status_bar)
        self.settings_panel_main = SettingsPanel(
            self.data_manager.get_settings(), 
            self.loc, 
            self, 
            context="window_main"
        )
        self.settings_panel_main.settings_changed.connect(self.data_manager.update_settings)
        self.settings_panel_main.hide()
        self.settings_panel_main.installEventFilter(self)
        self._setup_shortcuts()
        self.notes_panel.notes_editor.textChanged.connect(self._update_word_count)
        self.notes_panel.tags_updated.connect(self._rebuild_tag_chips)
        self.left_toggle.toggled.connect(self._on_left_toggle)
        self.right_toggle.toggled.connect(self._on_right_toggle)
        self.notes_panel.notes_editor.textChanged.connect(self.on_data_changed)
        self.notes_panel.notes_editor.textChanged.connect(self._update_to_task_btn_state)
        self.notes_panel.notes_editor.cursorPositionChanged.connect(self._update_to_task_btn_state)
        self.notes_panel.search_input.textChanged.connect(self._sync_tree_filter)
        self.notes_panel.tag_filter_combo.currentIndexChanged.connect(self._sync_tree_filter)
        self.tree_sidebar.folder_selected.connect(self.edit_folder_description)
        self.tree_sidebar.note_selected.connect(self.edit_note)
        self.tree_sidebar.selection_cleared.connect(self.clear_editor)
        self.notes_panel.save_button.clicked.disconnect()
        self.notes_panel.save_button.clicked.connect(self.save_current_item)
        self.notes_panel.note_created.connect(self.tree_sidebar.on_note_created)
        self.notes_panel.note_deleted.connect(self.tree_sidebar.on_note_deleted)
        self.tree_sidebar.note_deleted_from_tree.connect(self.notes_panel.delete_note_by_timestamp)
        self.notes_panel.note_saved.connect(lambda ts: self.tree_sidebar.refresh_aliases())
        self._update_to_task_btn_state()
        self.notes_panel.notes_editor_label.hide()
        self.retranslate_ui()
        self.apply_theme(self.data_manager.get_settings())
        self._restore_window_state_or_set_ratio()
        self._apply_left_right_visibility()
        self._rebuild_tag_chips(self.notes_panel.all_tags)
        self._update_word_count()
        self.clear_editor()
        self._first_show = True # Флаг для первого показа

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._restore_splitter_sizes()
            self._first_show = False

    def _on_splitter_moved(self, pos, index):
        """Вызывается при движении сплиттера."""
        sizes = self.splitter.sizes()
        self.data_manager.settings["window_splitter_sizes"] = sizes
        self.data_manager.save_settings()
        self.splitter_sizes_changed.emit(sizes) # Отправляем сигнал с новыми размерами

    def _restore_splitter_sizes(self):
        sizes = self.data_manager.get_settings().get("window_splitter_sizes", [250, 500, 350])
        self.splitter.setSizes(sizes)

    def _on_resize_finished(self):
        self.resize_overlay.hide()
        self._restore_window_state_or_set_ratio(force_recalc=True)
        self._is_resizing = False

    def _create_themed_menu(self):
        menu = QMenu(self)
        settings = self.data_manager.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border_color = "#555" if is_dark else "#ced4da"
        
        stylesheet = f"""
            QMenu {{ background-color: {comp_bg}; color: {text}; border: 1px solid {border_color}; border-radius: 6px; padding: 5px; }}
            QMenu::item {{ padding: 6px 15px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {accent}; color: white; }}
            QMenu::separator {{ height: 1px; background-color: {border_color}; margin: 5px 10px; }}
        """
        menu.setStyleSheet(stylesheet)
        return menu

    def edit_folder_description(self, item):
        self.save_current_item()
        self.current_edit_target = ("folder", item)
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        self.tree_sidebar.pending_target_folder = item
        self.notes_panel.clear_for_new_note(force=True)
        self.editor_context_label.setText(f"<b>Новая заметка в папке:</b> {nd.get('name', '')}")
        self.notes_panel.zen_button.setEnabled(False)
        self.to_task_btn.setEnabled(False)
        self.on_data_changed()

    def edit_note(self, item):
        self.save_current_item()
        self.current_edit_target = ("note", item)
        nd = item.data(0, Qt.ItemDataRole.UserRole) or {}
        ts = nd.get("timestamp")
        if ts: self.notes_panel.find_and_select_note_by_timestamp(ts)
        self.notes_panel.zen_button.setEnabled(True)
        self._update_to_task_btn_state()
        self.editor_context_label.setText(f"<b>{self.loc.get('note_editing', 'Редактирование заметки')}</b>")

    def clear_editor(self):
        self.save_current_item()
        self.current_edit_target = None
        self.tree_sidebar.pending_target_folder = self.tree_sidebar.tree.invisibleRootItem()
        self.notes_panel.clear_for_new_note(force=True)
        self.editor_context_label.setText(f"<b>{self.loc.get('new_note_title', 'Новая заметка')}</b>")
    
    def save_current_item(self):
        if self.notes_panel.is_dirty: self.notes_panel.save_current_note()

    def _toggle_audio_view(self):
        self.right_stack.setCurrentIndex(1 if self.right_stack.currentIndex() == 0 else 0)
    
    def _toggle_settings_panel_main(self):
        if self.settings_panel_main.isVisible():
            self.settings_panel_main.hide()
            if self._overlay:
                self._overlay.hide()
            return

        if not self._overlay:
            self._overlay = QWidget(self.nativeParentWidget()) # Используем родителя trigger'а
            self._overlay.setObjectName("settingsOverlay")
            self._overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self._overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._overlay.setStyleSheet("background: transparent;")
            self._overlay.mousePressEvent = self._overlay_clicked

        ### ИЗМЕНЕНИЕ: Позиционирование относительно всего экрана ###
        screen_rect = self.screen().geometry()
        self._overlay.setGeometry(screen_rect)
        self._overlay.show()

        self.settings_panel_main.setParent(self._overlay)
        panel_size = self.settings_panel_main.sizeHint()
        # Вычисляем центр экрана
        x = screen_rect.x() + (screen_rect.width() - panel_size.width()) // 2
        y = screen_rect.y() + (screen_rect.height() - panel_size.height()) // 2
        self.settings_panel_main.move(x, y)
        
        self.settings_panel_main.show()
        self.settings_panel_main.raise_()

    def _overlay_clicked(self, event):
        if not self.settings_panel_main.geometry().contains(event.pos()):
            self.settings_panel_main.hide()
            self._overlay.hide()

    def _restore_splitter_sizes(self):
        sizes = self.data_manager.get_settings().get("window_splitter_sizes", [250, 500, 350])
        self.splitter.setSizes(sizes)
        
    def _save_splitter_sizes(self, pos, index):
        sizes = self.splitter.sizes()
        self.data_manager.settings["window_splitter_sizes"] = sizes
        self.data_manager.save_settings()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())
        
        if not self._is_resizing:
            self._is_resizing = True
            self.resize_overlay.setGeometry(self.splitter.geometry())
            self.resize_overlay.show()
            self.resize_overlay.raise_()
        self.resize_timer.start()

    def eventFilter(self, obj, event):
        if obj is self.settings_panel_main and event.type() == QEvent.Type.Hide:
            if self._overlay and self._overlay.isVisible():
                self._overlay.hide()
        return super().eventFilter(obj, event)

    def load_note_tree(self, tree_data: list):
        self.tree_sidebar.set_model(tree_data)
        self._sync_tree_filter()

    def get_note_tree_data(self) -> list: return self.tree_sidebar.get_model()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.clear_editor)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_current_item)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.notes_panel.search_input.setFocus())
        QShortcut(QKeySequence("F7"), self, activated=lambda: self.left_toggle.toggle())
        QShortcut(QKeySequence("F6"), self, activated=lambda: self.right_toggle.toggle())
        QShortcut(QKeySequence("Ctrl++"), self, activated=lambda: self._zoom_editor(+1))
        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self._zoom_editor(+1))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._zoom_editor(-1))
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self._zoom_editor_reset)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close)
        QShortcut(QKeySequence("Space"), self, activated=self._audio_toggle_play_pause)
        QShortcut(QKeySequence("Delete"), self, activated=self._audio_remove_selected)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._audio_add_files)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self._audio_add_folder)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=self._audio_prev)
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=self._audio_next)
        QShortcut(QKeySequence("M"), self, activated=self.audio_widget._toggle_mute)
    
    def _is_player_active(self):
        return hasattr(self, "right_stack") and self.right_stack.currentIndex() == 1

    def _audio_toggle_play_pause(self):
        if self._is_player_active(): self.data_manager.global_audio.toggle_play_pause()
    def _audio_prev(self):
        if self._is_player_active(): self.data_manager.global_audio.prev()
    def _audio_next(self):
        if self._is_player_active(): self.data_manager.global_audio.next()
    def _audio_add_files(self):
        if self._is_player_active(): self.audio_widget._add_files()
    def _audio_add_folder(self):
        if self._is_player_active(): self.audio_widget._add_folder()
    def _audio_remove_selected(self):
        if self._is_player_active(): self.audio_widget._remove_selected()

    def _restore_window_state_or_set_ratio(self, force_recalc=False):
        st = self.data_manager.get_settings()
        if not force_recalc and st.get("window_geometry"):
            try: self.restoreGeometry(QByteArray.fromHex(st["window_geometry"].encode("ascii")))
            except Exception: pass
        
        min_left = st.get("window_min_width_left", 260)
        min_right = st.get("window_min_width_right", 380)
        
        if sides := st.get("window_splitter_sides"):
            try:
                center_w = self.splitter.width() - sides[0] - sides[1] - (self.splitter.handleWidth() * 2)
                self.splitter.setSizes([sides[0], max(self.center_container.minimumWidth(), center_w), sides[1]])
                return
            except Exception: pass
        
        center_w = self.splitter.width() - min_left - min_right - (self.splitter.handleWidth() * 2)
        self.splitter.setSizes([min_left, max(self.center_container.minimumWidth(), center_w), min_right])

    def _apply_left_right_visibility(self):
        st = self.data_manager.get_settings()
        lv = st.get("window_left_visible", True)
        rv = st.get("window_right_visible", True)
        self.left_container.setVisible(lv)
        self.right_container.setVisible(rv)
        self.left_toggle.setChecked(lv)
        self.right_toggle.setChecked(rv)
        
    def _ensure_nonzero_split_sizes(self):
        sizes = self.splitter.sizes()
        min_left = self.data_manager.get_settings().get("window_min_width_left", 260)
        min_right = self.data_manager.get_settings().get("window_min_width_right", 380)
        if self.left_container.isVisible() and sizes[0] < min_left: sizes[0] = min_left
        if self.center_container.isVisible() and sizes[1] < self.center_container.minimumWidth(): sizes[1] = self.center_container.minimumWidth()
        if self.right_container.isVisible() and sizes[2] < min_right: sizes[2] = min_right
        self.splitter.setSizes(sizes)
        
    def _on_left_toggle(self, checked):
        self.left_container.setVisible(checked)
        self._ensure_nonzero_split_sizes()
        self.data_manager.get_settings()["window_left_visible"] = checked
        self.data_manager.save_settings()
        
    def _on_right_toggle(self, checked):
        self.right_container.setVisible(checked)
        self._ensure_nonzero_split_sizes()
        self.data_manager.get_settings()["window_right_visible"] = checked
        self.data_manager.save_settings()

    def _add_selection_as_task(self):
        cursor = self.notes_panel.notes_editor.textCursor()
        text = cursor.selectedText().strip()
        if not text:
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            text = cursor.selectedText().strip()
        text = text.replace('\u2029', ' ').replace('\n', ' ').strip()
        if text: self.tasks_panel.add_task(text); self.data_manager.save_app_data()
        
    def _collect_tag_freq(self):
        freq = {}
        for note in self.data_manager.get_all_notes_from_cache():
            for tag in self.notes_panel.find_tags(note.get("text", "")):
                freq[tag] = freq.get(tag, 0) + 1
        return freq
        
    def _rebuild_tag_chips(self, tags=None):
        while self.chips_layout.count():
            if w := self.chips_layout.takeAt(0).widget(): w.deleteLater()
        freq = self._collect_tag_freq()
        items = sorted(freq.items(), key=lambda t: t[1], reverse=True)
        if not items and tags: items = [(t, 1) for t in sorted(tags)]
        items = items[:20]
        if items: self.chips_layout.addWidget(QLabel(self.loc.get("tags_label")))
        for tag, _ in items:
            btn = QPushButton(f"#{tag}")
            btn.setObjectName("chipButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, t=tag: self._insert_tag_into_editor(t))
            self.chips_layout.addWidget(btn)
        self.chips_layout.addStretch()
        
    def _insert_tag_into_editor(self, tag):
        ed = self.notes_panel.notes_editor
        cursor = ed.textCursor()
        cursor.insertText(f"#{tag} ")
        ed.setTextCursor(cursor)
        ed.setFocus()
        
    def _update_word_count(self):
        text = self.notes_panel.notes_editor.toPlainText().strip()
        words = len(text.split()) if text else 0
        self.word_count_label.setText(f"{self.loc.get('word_count_label')}: {words}")
        
    def _update_to_task_btn_state(self):
        cursor = self.notes_panel.notes_editor.textCursor()
        text = cursor.selectedText().strip()
        if not text:
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            text = cursor.selectedText().strip()
        self.to_task_btn.setEnabled(bool(text))
        
    def _sync_tree_filter(self):
        visible_ts = set()
        for i in range(self.notes_panel.note_list_widget.count()):
            it = self.notes_panel.note_list_widget.item(i)
            if not it.isHidden():
                if ts := (it.data(Qt.ItemDataRole.UserRole) or {}).get("timestamp"):
                    visible_ts.add(ts)
        self.tree_sidebar.apply_visibility(visible_ts)
        
    def retranslate_ui(self):
        self.tasks_panel.retranslate_ui()
        self.notes_panel.retranslate_ui()
        self.setWindowTitle("Ассистент")
        self.to_panel_button.setText(self.loc.get("to_panel_button"))
        self.to_panel_button.setToolTip(self.loc.get("to_panel_tooltip"))
        self.left_toggle.setText(self.loc.get("left_column_toggle"))
        self.left_toggle.setToolTip(self.loc.get("left_column_tooltip"))
        self.right_toggle.setText(self.loc.get("right_column_toggle"))
        self.right_toggle.setToolTip(self.loc.get("right_column_tooltip"))
        self.to_task_btn.setText(self.loc.get("to_task_btn"))
        self.to_task_btn.setToolTip(self.loc.get("to_task_tooltip"))
        self.audio_toggle_btn.setToolTip(self.loc.get("audio_toggle_tooltip"))
        self.settings_toggle_btn.setToolTip(self.loc.get("settings_title"))
        self.set_status_saved()
        
    def apply_theme(self, settings):
        is_dark, accent, bg, text, list_text = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        panel_bg = QColor(comp_bg).lighter(108).name() if is_dark else QColor(comp_bg).lighter(103).name()
        border = "#555" if is_dark else "#ced4da"
        qtool_hover = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.06)"
        zebra1 = "rgba(0,0,0,0.02)" if not is_dark else "rgba(255,255,255,0.02)"
        
        stylesheet = f"""
            QWidget#MainWindow {{ background-color:{bg}; }}
            QWidget#settingsOverlay, QFrame#resizeOverlay {{ background: rgba(0,0,0,0.5); }}
            QFrame#resizeOverlay QLabel {{ color: white; font-size: 16pt; font-weight: bold; background: transparent; }}
            QWidget, QLabel {{ color:{text}; }}
            QStatusBar {{ background:{QColor(bg).name()}; border-top:1px solid {border}; }}
            QLabel#titleLabel {{ font-size:16px; font-weight:bold; }}
            QLabel#contextLabel {{ color:{accent}; font-weight:bold; padding-left: 2px; }}
            QWidget#cardContainer, QFrame#audioWidgetContainer {{
                background-color:{panel_bg}; border:1px solid {border}; border-radius:8px;
            }}
            QLineEdit, QTextEdit, QComboBox, QListWidget, QTreeWidget#NotesTree {{
                background-color:{comp_bg}; border:1px solid {border};
                border-radius:6px; padding:6px;
            }}
            QComboBox QAbstractItemView{{
                background-color:{comp_bg};color:{text};border:1px solid {border};
                selection-background-color:{accent};selection-color:white;outline:0px;
            }}
            QListWidget::item, QTreeWidget#NotesTree::item {{
                color:{list_text}; padding:6px; border-radius:4px;
            }}
            QTreeWidget#NotesTree::item:alternate {{ background-color: {zebra1}; }}
            QListWidget::item:hover, QTreeWidget#NotesTree::item:hover {{
                background-color:rgba(128,128,128,0.15);
            }}
            QListWidget::item:selected, QTreeWidget#NotesTree::item:selected {{
                background-color:{accent}; color:white;
            }}
            QListWidget#TaskList::indicator {{
                width: 16px; height: 16px;
                border: 2px solid {'#888' if is_dark else '#adb5bd'};
                border-radius: 3px; background: transparent;
            }}
            QListWidget#TaskList::indicator:hover {{ border-color: {accent}; }}
            QListWidget#TaskList::indicator:checked {{ background-color: {accent}; border-color: {accent}; }}
            
            QToolButton, QPushButton#toPanelButton, QPushButton {{
                background-color:{comp_bg}; color:{text}; border:1px solid {border};
                border-radius:4px; padding: 5px 10px;
            }}
            QToolButton:hover, QPushButton:hover {{ background-color: {qtool_hover}; }}
            QToolButton:checked {{ background-color:{accent}; color:white; border-color:{accent}; }}
            
            QCheckBox{{ spacing:8px; color:{text}; }}
            QCheckBox::indicator{{
                width:16px; height:16px; border:2px solid {'#888' if is_dark else '#adb5bd'};
                border-radius:3px; background:{'#2d2d2d' if is_dark else '#ffffff'};
            }}
            QCheckBox::indicator:hover{{ border-color:{accent}; }}
            QCheckBox::indicator:checked{{ border-color:{accent}; background:{accent}; }}
            
            QSplitter::handle {{ background-color:transparent; }}
            QSplitter::handle:hover {{ background-color:rgba(128,128,128,0.15); }}
            QSplitter::handle:horizontal {{ width:12px; }}
            QPushButton#chipButton {{ padding: 3px 8px; border-radius:10px; }}
            QScrollArea#chipsScroll {{
                border: none; background: transparent; min-height: 34px; max-height: 34px;
            }}
            QWidget#chipsHost {{ background: transparent; }}
        """
        self.setStyleSheet(stylesheet)
        self.audio_toggle_btn.setIcon(ThemedIconProvider.icon("note", settings))
        self.settings_toggle_btn.setIcon(ThemedIconProvider.icon("gear", settings))
        self.close_button.setIcon(ThemedIconProvider.icon("close", settings))
        if hasattr(self, "audio_widget"): self.audio_widget.apply_theme_icons(settings)
        s = settings.copy()
        if self.window_editor_font_size: s["window_editor_font_size"] = self.window_editor_font_size
        self.notes_panel.apply_editor_style(s)
        self.tree_sidebar.refresh_aliases()
        if hasattr(self, "settings_panel_main"): self.settings_panel_main.apply_styles()

        min_left = settings.get("window_min_width_left", 260)
        min_right = settings.get("window_min_width_right", 380)
        self.left_container.setMinimumWidth(min_left)
        self.right_container.setMinimumWidth(min_right)
        s = settings.copy()
        if self.window_editor_font_size: s["window_editor_font_size"] = self.window_editor_font_size
        self.notes_panel.apply_editor_style(s)
        
        self.tree_sidebar.refresh_aliases()
        if hasattr(self, "settings_panel_main"):
            self.settings_panel_main.apply_styles()
        
    def on_data_changed(self):
        is_folder_edit = self.current_edit_target and self.current_edit_target[0] == "folder"
        is_dirty = self.notes_panel.is_dirty
        if is_folder_edit: is_dirty = self.notes_panel.notes_editor.toPlainText() != self.notes_panel.saved_text
        if is_dirty:
            self.status_text.setText(self.loc.get("unsaved_changes_status"))
            self.status_text.setStyleSheet("color: #dc3545;")
        else: self.set_status_saved()
        
    def set_status_saved(self):
        self.status_text.setText(self.loc.get("data_saved_status"))
        self.status_text.setStyleSheet("color: #28a745;")
        
    def _save_splitter_sizes(self):
        sizes = self.splitter.sizes()
        if len(sizes) == 3:
            st = self.data_manager.get_settings()
            st["window_splitter_sides"] = [sizes[0], sizes[2]]
            self.data_manager.save_settings()

    def closeEvent(self, event):
        self.save_current_item()
        st = self.data_manager.get_settings()
        try:
            st["window_geometry"] = self.saveGeometry().toHex().data().decode("ascii")
            self._save_splitter_sizes()
            st["window_editor_font_size"] = self.window_editor_font_size or 0
            st["window_left_visible"] = self.left_container.isVisible()
            st["window_right_visible"] = self.right_container.isVisible()
        except Exception as e:
            print(f"Error saving window state: {e}")
        self.data_manager.save_settings()
        self.data_manager.save_app_data(force_container=self)
        self.window_closed.emit()
        super().closeEvent(event)
            
    def _zoom_editor(self, delta):
        st = self.data_manager.get_settings()
        current = self.window_editor_font_size or st.get("zen_font_size", 18)
        new_size = max(8, min(72, int(current) + delta))
        self.window_editor_font_size = new_size
        s = st.copy()
        s["window_editor_font_size"] = new_size
        self.notes_panel.apply_editor_style(s)
        
    def _zoom_editor_reset(self):
        self.window_editor_font_size = 0
        self.notes_panel.apply_editor_style(self.data_manager.get_settings())

class GlobalAudioController(QObject):
    playlists_changed = pyqtSignal(list, str)
    current_playlist_changed = pyqtSignal(str)
    tracks_changed = pyqtSignal(list)
    current_index_changed = pyqtSignal(int)
    state_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._relay_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self._playlists_file = os.path.join(base_dir, "audio_playlists.json")
        self.playlists = {}
        self.playlist_order = []
        self.current_playlist = ""
        self.index = -1
        self.audio_output.setVolume(0.5)
        self._load_playlists()

# В классе GlobalAudioController
    def _load_playlists(self):
        try:
            if not os.path.exists(self._playlists_file): raise FileNotFoundError
            with open(self._playlists_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.playlists = data.get("playlists", {})
            self.playlist_order = data.get("order", list(self.playlists.keys()))
            self.current_playlist = data.get("current", "")
        except (FileNotFoundError, json.JSONDecodeError):
            self.playlists = {}
            self.playlist_order = []
            self.current_playlist = ""
            
        # --- НАЧАЛО НОВОГО КОДА ---
        # Проверяем и создаем плейлист "Zen" по умолчанию, если его нет
        if "Zen" not in self.playlists:
            zen_dir = ""
            try:
                # Определяем путь к папке zen_audio
                base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                zen_dir = os.path.join(base_dir, "zen_audio")
            except Exception:
                pass

            if zen_dir and os.path.isdir(zen_dir):
                exts = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
                zen_tracks = [os.path.join(zen_dir, f) for f in os.listdir(zen_dir) if f.lower().endswith(exts)]
                if zen_tracks:
                    self.playlists["Zen"] = zen_tracks
                    if "Zen" not in self.playlist_order:
                        self.playlist_order.insert(0, "Zen") # Добавляем в начало
                    self._save_playlists() # Сразу сохраняем, чтобы он был при следующем запуске
        # --- КОНЕЦ НОВОГО КОДА ---

        if not self.playlists: self.playlists["Default"] = []
        if not self.playlist_order: self.playlist_order = list(self.playlists.keys())
        if not self.current_playlist or self.current_playlist not in self.playlists:
            self.current_playlist = self.playlist_order[0] if self.playlist_order else ""
        self._emit_all()


    def _save_playlists(self):
        try:
            data = {"playlists": self.playlists, "order": self.playlist_order, "current": self.current_playlist}
            with open(self._playlists_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except (IOError, TypeError) as e:
            print(f"Не удалось сохранить плейлисты: {e}")

    def _emit_all(self):
        names = [n for n in self.playlist_order if n in self.playlists]
        if not names:
            names = list(self.playlists.keys())
            self.playlist_order = names[:]
        if self.current_playlist not in names and names:
            self.current_playlist = names[0]
        self.playlists_changed.emit(names, self.current_playlist)
        self.current_playlist_changed.emit(self.current_playlist)
        self.tracks_changed.emit(self.get_tracks())
        self.current_index_changed.emit(self.index)
        self.state_changed.emit(self.player.playbackState())

    def get_tracks(self):
        return list(self.playlists.get(self.current_playlist, []))

    def switch_playlist_by_offset(self, delta: int):
        names = [n for n in self.playlist_order if n in self.playlists]
        if not names: return
        try:
            i = names.index(self.current_playlist)
            i = (i + delta) % len(names)
            self.set_current_playlist(names[i])
        except ValueError:
            if names: self.set_current_playlist(names[0])
    
    def set_current_playlist(self, name: str):
        if name not in self.playlists: return
        self.current_playlist = name
        self.index = -1
        self._emit_all()
        self._save_playlists()
    
    def add_playlist(self, name: str):
        name = name.strip() or "New"
        base = name
        k = 1
        while name in self.playlists:
            k += 1
            name = f"{base} {k}"
        self.playlists[name] = []
        self.playlist_order.append(name)
        self.set_current_playlist(name)
    
    def rename_playlist(self, old: str, new: str):
        if old not in self.playlists: return
        new = new.strip() or old
        if new == old or new in self.playlists: return
        self.playlists[new] = self.playlists.pop(old)
        self.playlist_order = [new if x == old else x for x in self.playlist_order]
        if self.current_playlist == old: self.current_playlist = new
        self._emit_all()
        self._save_playlists()
    
    def delete_playlist(self, name: str):
        if name not in self.playlists or len(self.playlists) <= 1: return
        del self.playlists[name]
        self.playlist_order = [x for x in self.playlist_order if x != name]
        if self.current_playlist == name:
            self.current_playlist = self.playlist_order[0] if self.playlist_order else ""
            self.index = -1
        self._emit_all()
        self._save_playlists()
    
    def add_files(self, paths: list[str]):
        if not paths: return
        tracks = self.get_tracks()
        added = 0
        for p in paths:
            if p and os.path.isfile(p) and p not in tracks:
                tracks.append(p)
                added += 1
        if added:
            self.playlists[self.current_playlist] = tracks
            self.tracks_changed.emit(self.get_tracks())
            self._save_playlists()
    
    def add_folder(self, folder_path: str):
        if not folder_path or not os.path.isdir(folder_path): return
        exts = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
        tracks = self.get_tracks()
        added = 0
        try:
            for root, _, files in os.walk(folder_path):
                for f in files:
                    if f.lower().endswith(exts):
                        p = os.path.join(root, f)
                        if p not in tracks:
                            tracks.append(p)
                            added += 1
        except Exception as e:
            print("add_folder error:", e)
        if added:
            self.playlists[self.current_playlist] = tracks
            self.tracks_changed.emit(self.get_tracks())
            self._save_playlists()
    
    def remove_indexes(self, idxs: list[int]):
        if not idxs: return
        tracks = self.get_tracks()
        idxs = sorted(set([i for i in idxs if 0 <= i < len(tracks)]), reverse=True)
        cur_path = self.player.source().toLocalFile() if self.player.source().isValid() else None
        for i in idxs: del tracks[i]
        self.playlists[self.current_playlist] = tracks
        if cur_path not in tracks:
            self.index = -1
            self.stop()
        else:
            self.index = tracks.index(cur_path)
        self.tracks_changed.emit(self.get_tracks())
        self.current_index_changed.emit(self.index)
        self._save_playlists()
    
    def set_order(self, new_files_list: list[str], current_path: str | None = None):
        self.playlists[self.current_playlist] = list(new_files_list or [])
        if current_path and current_path in self.playlists[self.current_playlist]:
            self.index = self.playlists[self.current_playlist].index(current_path)
            self.current_index_changed.emit(self.index)
        elif not self.playlists[self.current_playlist]:
            self.index = -1
            self.stop()
        self.tracks_changed.emit(self.get_tracks())
        self._save_playlists()

    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def play_index(self, i: int):
        tracks = self.get_tracks()
        if not tracks: return
        i = max(0, min(len(tracks) - 1, i))
        self.index = i
        self.player.setSource(QUrl.fromLocalFile(tracks[self.index]))
        self.player.play()
        self.current_index_changed.emit(self.index)

    def toggle_play_pause(self):
        if self.is_playing():
            self.player.pause()
        else:
            tracks = self.get_tracks()
            if self.index < 0 and tracks:
                self.index = 0
                self.current_index_changed.emit(self.index)
                self.player.setSource(QUrl.fromLocalFile(tracks[self.index]))
            if tracks:
                self.player.play()

    def next(self):
        tracks = self.get_tracks()
        if not tracks: return
        self.play_index((self.index + 1) % len(tracks))

    def prev(self):
        tracks = self.get_tracks()
        if not tracks: return
        self.play_index((self.index - 1) % len(tracks))

    def stop(self):
        self.player.stop()

    def set_volume(self, v: int):
        new_volume_float = max(0.0, min(1.0, v / 100.0))
        if self.audio_output.volume() != new_volume_float:
            self.audio_output.setVolume(new_volume_float)

    def volume(self) -> int:
        return int(round(self.audio_output.volume() * 100))

    def toggle_mute(self):
        self.audio_output.setMuted(not self.audio_output.isMuted())

    def is_muted(self) -> bool:
        return self.audio_output.isMuted()

    def _relay_state_changed(self, st):
        self.state_changed.emit(st)

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.index < len(self.get_tracks()) - 1:
                self.next()
            else:
                self.stop()
                self.index = -1
                self.current_index_changed.emit(self.index)

class GlobalAudioWidget(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, controller: GlobalAudioController, loc: LocalizationManager, parent=None):
        super().__init__(parent)
        self.ctrl = controller
        self.loc = loc
        self.is_slider_pressed = False
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(6)
        self.prev_pl_btn = QToolButton()
        self.next_pl_btn = QToolButton()
        self.playlist_label = QPushButton()
        self.playlist_label.setFixedHeight(32)
        self.playlist_label.setFlat(True)
        self.playlist_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.playlist_label.setObjectName("playlistLabel")
        self.playlist_label.clicked.connect(self._open_playlist_menu)
        head.addWidget(self.prev_pl_btn)
        head.addWidget(self.playlist_label, 1)
        head.addWidget(self.next_pl_btn)
        main_layout.addLayout(head)

        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(6)
        self.time_label = QLabel("00:00")
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.duration_label = QLabel("00:00")
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider, 1)
        progress_layout.addWidget(self.duration_label)
        main_layout.addLayout(progress_layout)

        transport = QHBoxLayout()
        transport.setSpacing(6)
        self.prev_btn = QToolButton()
        self.play_btn = QToolButton()
        self.stop_btn = QToolButton()
        self.next_btn = QToolButton()
        transport.addStretch()
        transport.addWidget(self.prev_btn)
        transport.addWidget(self.play_btn)
        transport.addWidget(self.stop_btn)
        transport.addWidget(self.next_btn)
        transport.addStretch()
        main_layout.addLayout(transport)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        main_layout.addWidget(self.list, 1)

        self.audio_filebar = QWidget()
        fb = QHBoxLayout(self.audio_filebar)
        fb.setContentsMargins(0, 0, 0, 0)
        fb.setSpacing(8)
        self.audio_add_files_btn = QToolButton()
        self.audio_add_folder_btn = QToolButton()
        self.audio_remove_btn = QToolButton()
        self.audio_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.audio_vol_slider.setRange(0, 100)
        self.audio_vol_slider.setFixedSize(64, 16)
        self.audio_mute_btn = QToolButton()
        fb.addWidget(self.audio_add_files_btn)
        fb.addWidget(self.audio_add_folder_btn)
        fb.addWidget(self.audio_remove_btn)
        fb.addStretch()
        fb.addWidget(self.audio_vol_slider)
        fb.addWidget(self.audio_mute_btn)
        main_layout.addWidget(self.audio_filebar)

        self.prev_pl_btn.clicked.connect(lambda: self.ctrl.switch_playlist_by_offset(-1))
        self.next_pl_btn.clicked.connect(lambda: self.ctrl.switch_playlist_by_offset(1))
        self.prev_btn.clicked.connect(self.ctrl.prev)
        self.play_btn.clicked.connect(self.ctrl.toggle_play_pause)
        self.stop_btn.clicked.connect(self.ctrl.stop)
        self.next_btn.clicked.connect(self.ctrl.next)
        self.progress_slider.sliderMoved.connect(self.ctrl.player.setPosition)
        self.progress_slider.sliderPressed.connect(lambda: setattr(self, 'is_slider_pressed', True))
        self.progress_slider.sliderReleased.connect(lambda: setattr(self, 'is_slider_pressed', False))
        self.list.itemDoubleClicked.connect(self._play_selected)
        self.list.model().rowsMoved.connect(self._on_rows_moved)
        self.audio_add_files_btn.clicked.connect(self._add_files)
        self.audio_add_folder_btn.clicked.connect(self._add_folder)
        self.audio_remove_btn.clicked.connect(self._remove_selected)
        self.audio_vol_slider.valueChanged.connect(self.ctrl.set_volume)
        self.audio_mute_btn.clicked.connect(self._toggle_mute)

        self.ctrl.playlists_changed.connect(self._on_playlists_changed)
        self.ctrl.current_playlist_changed.connect(self._on_current_playlist)
        self.ctrl.tracks_changed.connect(self._reload_tracks)
        self.ctrl.current_index_changed.connect(self._on_current_changed)
        self.ctrl.state_changed.connect(self._on_state_changed)
        self.ctrl.player.positionChanged.connect(self._on_position_changed)
        self.ctrl.player.durationChanged.connect(self._on_duration_changed)
        self.ctrl.audio_output.volumeChanged.connect(self.update_slider_volume)
        self.ctrl.audio_output.mutedChanged.connect(lambda muted: self._update_mute_icon())
        
        self._on_playlists_changed(getattr(self.ctrl, "playlist_order", []), getattr(self.ctrl, "current_playlist", ""))
        self._reload_tracks(self.ctrl.get_tracks())
        self._on_current_changed(getattr(self.ctrl, "index", -1))
        
        dm = self.ctrl.parent()
        if dm and hasattr(dm, 'get_settings'):
            self.apply_theme_icons(dm.get_settings())
        
        self.update_slider_volume(self.ctrl.audio_output.volume())
        self._on_duration_changed(self.ctrl.player.duration())

    # ДОБАВИТЬ ЭТОТ МЕТОД ВНУТРЬ КЛАССА GlobalAudioWidget
    def apply_zen_style(self, floating_fg, component_bg, hover_bg, border_color):
        """Применяет специальный стиль для режима Zen."""
        stylesheet = f"""
            /* Стили для плеера в ZenMode */
            QListWidget {{
                background-color: {component_bg};
                color: {floating_fg};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 5px;
                color: {floating_fg};
            }}
            QListWidget::item:selected {{
                background-color: {hover_bg};
                border-radius: 4px;
            }}

            QPushButton#playlistLabel {{
                color: {floating_fg};
                background-color: transparent;
                border: none;
                text-align: center;
                font-weight: bold;
            }}
            QPushButton#playlistLabel:hover {{
                background-color: {hover_bg};
                border-radius: 4px;
            }}

            QLabel {{
                color: {floating_fg};
                background: transparent;
            }}

            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: {hover_bg};
            }}
            
            QSlider::groove:horizontal {{
                background: {border_color};
                height: 3px;
                border-radius: 1px;
            }}
            QSlider::handle:horizontal {{
                background: {floating_fg};
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::sub-page:horizontal {{
                background: {floating_fg};
            }}
        """
        self.setStyleSheet(stylesheet)

    def update_slider_volume(self, volume_float):
        if hasattr(self, 'audio_vol_slider'):
            new_value = int(round(volume_float * 100))
            self.audio_vol_slider.blockSignals(True)
            self.audio_vol_slider.setValue(new_value)
            self.audio_vol_slider.blockSignals(False)

    def apply_theme_icons(self, settings: dict):
        self.next_pl_btn.setIcon(ThemedIconProvider.icon("chev_r", settings))
        self.prev_pl_btn.setIcon(ThemedIconProvider.icon("chev_l", settings))
        self.prev_btn.setIcon(ThemedIconProvider.icon("prev", settings))
        self.stop_btn.setIcon(ThemedIconProvider.icon("stop", settings))
        self.next_btn.setIcon(ThemedIconProvider.icon("next", settings))
        self.audio_add_files_btn.setIcon(ThemedIconProvider.icon("add_file", settings))
        self.audio_add_folder_btn.setIcon(ThemedIconProvider.icon("add_folder", settings))
        self.audio_remove_btn.setIcon(ThemedIconProvider.icon("trash", settings))
        self._on_state_changed(self.ctrl.player.playbackState())
        self._update_mute_icon()
        self.retranslate_ui()

    def retranslate_ui(self):
        self.playlist_label.setText(self.ctrl.current_playlist or self.loc.get("playlist", "Плейлист"))
        self.audio_add_files_btn.setToolTip(self.loc.get("audio_add_files", "Добавить файлы"))
        self.audio_add_folder_btn.setToolTip(self.loc.get("audio_add_folder", "Добавить папку"))
        self.audio_remove_btn.setToolTip(self.loc.get("audio_remove_selected", "Удалить выбранные"))
        self.audio_vol_slider.setToolTip(self.loc.get("audio_volume", "Громкость"))
        self._update_mute_icon()
        
    def _on_position_changed(self, pos):
        if not self.is_slider_pressed:
            self.progress_slider.setValue(pos)
        self.time_label.setText(f"{pos//60000:02d}:{pos//1000%60:02d}")

    def _on_duration_changed(self, dur):
        self.progress_slider.setRange(0, dur)
        self.duration_label.setText(f"{dur//60000:02d}:{dur//1000%60:02d}")
        if dur > 0:
            self._on_position_changed(self.ctrl.player.position())

    def _on_playlists_changed(self, names, current):
        self.playlist_label.setText(current or (names[0] if names else self.loc.get("playlist", "Плейлист")))

    def _on_current_playlist(self, name: str):
        self.playlist_label.setText(name or self.loc.get("playlist", "Плейлист"))

    def _open_playlist_menu(self):
        dm = self.ctrl.parent()
        settings = dm.get_settings() if dm and hasattr(dm, 'get_settings') else DEFAULT_SETTINGS
        menu = QMenu(self)
        is_dark, accent, bg, text, _ = theme_colors(settings)
        border = "#555" if is_dark else "#ced4da"
        comp = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        menu.setStyleSheet(f"QMenu{{background-color:{comp};color:{text};border:1px solid {border};border-radius:6px;padding:5px;}} "
                           f"QMenu::item{{padding:6px 15px;}} QMenu::item:selected{{background-color:{accent};color:white;}} "
                           f"QMenu::separator{{height:1px;background:{border};margin:6px 10px;}}")
        menu.addAction(self.loc.get("add_list_menu"), self._add_playlist)
        menu.addAction(self.loc.get("rename_list_menu"), self._rename_playlist)
        if len(self.ctrl.playlists) > 1:
            menu.addAction(self.loc.get("delete_list_menu"), self._delete_playlist)
        menu.exec(self.playlist_label.mapToGlobal(self.playlist_label.rect().bottomLeft()))

    def _add_playlist(self):
        name, ok = QInputDialog.getText(self, self.loc.get("add_list_menu"), self.loc.get("new_list_prompt"))
        if ok and name.strip():
            self.ctrl.add_playlist(name.strip())

    def _rename_playlist(self):
        cur = self.ctrl.current_playlist
        name, ok = QInputDialog.getText(self, self.loc.get("rename_list_menu"), self.loc.get("rename_list_prompt"), QLineEdit.EchoMode.Normal, cur)
        if ok and name.strip() and name.strip() != cur:
            self.ctrl.rename_playlist(cur, name.strip())

    def _delete_playlist(self):
        cur = self.ctrl.current_playlist
        if len(self.ctrl.playlists) <= 1: return
        ok = QMessageBox.question(self, self.loc.get("delete_list_menu"), self.loc.get("delete_list_confirm").format(list_name=cur))
        if ok == QMessageBox.StandardButton.Yes:
            self.ctrl.delete_playlist(cur)

    def _reload_tracks(self, files: list):
        self.list.clear()
        for i, path in enumerate(files):
            it = QListWidgetItem(f"{i+1}. {os.path.basename(path)}")
            it.setData(Qt.ItemDataRole.UserRole, path)
            self.list.addItem(it)

    def _on_rows_moved(self, parent, start, end, destParent, destRow):
        new_files = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]
        current_path = self.ctrl.player.source().toLocalFile() if self.ctrl.player.source().isValid() else None
        self.ctrl.set_order(new_files, current_path)
        self._renumber()

    def _renumber(self):
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setText(f"{i+1}. {os.path.basename(it.data(Qt.ItemDataRole.UserRole))}")

    def _on_current_changed(self, idx: int):
        for i in range(self.list.count()):
            it = self.list.item(i)
            f = it.font()
            f.setBold(i == idx)
            it.setFont(f)
        if 0 <= idx < self.list.count():
            self.list.setCurrentRow(idx)
            self.list.scrollToItem(self.list.item(idx), QAbstractItemView.ScrollHint.PositionAtCenter)

    def _on_state_changed(self, st):
        dm = self.ctrl.parent()
        settings = dm.get_settings() if dm and hasattr(dm, 'get_settings') else DEFAULT_SETTINGS
        if st == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setIcon(ThemedIconProvider.icon("pause", settings))
            self.play_btn.setToolTip(self.loc.get("audio_pause", "Пауза"))
        else:
            self.play_btn.setIcon(ThemedIconProvider.icon("play", settings))
            self.play_btn.setToolTip(self.loc.get("audio_play", "Воспроизвести"))

    def _play_selected(self, item: QListWidgetItem):
        self.ctrl.play_index(self.list.row(item))

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.loc.get("audio_add_files", "Добавить файлы"), "", "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a);;All Files (*)")
        if paths:
            self.ctrl.add_files(paths)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.loc.get("audio_add_folder", "Добавить папку"), "")
        if folder:
            self.ctrl.add_folder(folder)

    def _remove_selected(self):
        rows = [self.list.row(it) for it in self.list.selectedItems()]
        self.ctrl.remove_indexes(rows)

    def _toggle_mute(self):
        self.ctrl.toggle_mute()

    def _update_mute_icon(self):
        dm = self.ctrl.parent()
        settings = dm.get_settings() if dm and hasattr(dm, 'get_settings') else DEFAULT_SETTINGS
        icon_name = "volume_mute" if self.ctrl.is_muted() else "volume"
        self.audio_mute_btn.setIcon(ThemedIconProvider.icon(icon_name, settings))
        self.audio_mute_btn.setToolTip(self.loc.get("audio_mute_on", "Включить звук") if self.ctrl.is_muted() else self.loc.get("audio_mute_off", "Выключить звук"))


class TriggerButton(QPushButton):
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, loc_manager):
        super().__init__("")
        self.setObjectName("trigger_button")
        self.loc = self.loc_manager = loc_manager
        self.settings = DEFAULT_SETTINGS.copy()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(20, 100)
        self.main_popup = None 
        self.main_window = None
        self.about_dialog = None
        self.zen_window = None
        self.zen_source_timestamp = None
        self.pending_zen_data = None
        self.is_entering_zen = False
        self.is_switching_to_window = False
        self.note_to_select_after_load = None
        self.all_notes_cache = []
        self.note_tree_cache = []
        self.notes_root_folder = "Заметки"
        self.global_audio = GlobalAudioController(self)
        self.zen_return_to_window_mode = False
        
        self.load_settings()
        self._load_and_validate_data()
        self.loc.language_changed.connect(self._on_language_changed)
        self.loc.set_language(self.settings.get("language", "ru_RU"))
        self.update_position_and_style()
        self.clicked.connect(self._on_left_click)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.create_backup)
        self.backup_timer.start(600000)
        QApplication.instance().aboutToQuit.connect(self.on_app_quit)
        self._popup_lock = False


    def on_app_quit(self):
        container = self._choose_ui()
        if container:
            self.save_app_data(force_container=container)
        
    def _on_left_click(self):
        if self.main_window and self.main_window.isVisible():
            self.main_window.activateWindow()
            return
        if self._popup_lock:
            return
        self._popup_lock = True
        QTimer.singleShot(400, lambda: setattr(self, "_popup_lock", False))
        
        if self.main_popup and self.main_popup.isVisible():
            self.main_popup.close()
        else:
            self.show_main_popup()

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
            settings = DEFAULT_SETTINGS.copy()
            settings.update(loaded_settings)
            self.settings = settings
        except (FileNotFoundError, json.JSONDecodeError):
            self.settings = DEFAULT_SETTINGS.copy()

    def get_settings(self):
        return self.settings

    def get_all_notes_from_cache(self):
        return self.all_notes_cache

    def _choose_ui(self):
        # Этот метод теперь также обновляет last_active_ui
        if self.main_window and self.main_window.isVisible():
            self.last_active_ui = self.main_window
            return self.main_window
        if self.main_popup and self.main_popup.isVisible():
            self.last_active_ui = self.main_popup
            return self.main_popup
        return None
        
    def _get_current_note_ts(self, container):
        if not container: return None
        try:
            if item := container.notes_panel.current_note_item:
                return (item.data(Qt.ItemDataRole.UserRole) or {}).get('timestamp')
        except Exception:
            pass
        return None

    def _on_language_changed(self):
        if self.main_popup: self.main_popup.retranslate_ui()
        if self.main_window: self.main_window.retranslate_ui()
        if self.zen_window: self.zen_window.retranslate_ui()
        if self.about_dialog: self.about_dialog.retranslate_ui()
        self.update_position_and_style()

    def update_position_and_style(self):
        screen = QApplication.primaryScreen().geometry()
        pos = self.settings.get("trigger_pos", "right")
        icon = ThemedIconProvider.icon("chev_l" if pos == "left" else "chev_r", self.settings, QSize(16, 16))
        self.setIcon(icon)
        self.setIconSize(QSize(16, 16))
        self.setText("")
        accent = self.settings.get("accent_color", "#007bff")
        style = f"background-color:{accent};color:white;"
        if pos == "left":
            self.move(0, int(screen.height() * 0.4))
            style += "border-top-right-radius:5px;border-bottom-right-radius:5px;border-left:none;"
        else:
            self.move(screen.width() - self.width(), int(screen.height() * 0.4))
            style += "border-top-left-radius:5px;border-bottom-left-radius:5px;border-right:none;"
        self.setStyleSheet(f"QPushButton#trigger_button{{{style}}} QPushButton#trigger_button:hover{{opacity:0.9;}}")

    def _on_context_menu(self, pos):
        menu = QMenu(self)
        menu.setObjectName("contextMenu")
        is_dark, accent, bg, text, _ = theme_colors(self.settings)
        border = "#555" if is_dark else "#ced4da"
        comp = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        menu.setStyleSheet(f"QMenu{{background-color:{comp};color:{text};border:1px solid {border};border-radius:6px;padding:5px;}} "
                           f"QMenu::item{{padding:6px 15px;}} QMenu::item:selected{{background-color:{accent};color:white;}} "
                           f"QMenu::separator{{height:1px;background:{border};margin:6px 10px;}}")
        menu.addAction(self.loc.get("about_menu"), self.show_about_dialog)
        menu.addAction(self.loc.get("open_window_menu"), self.show_main_window)
        menu.addSeparator()
        menu.addAction(self.loc.get("export_menu"), self.export_notes_to_markdown)
        menu.addAction(self.loc.get("restore_menu"), self.restore_from_backup)
        menu.addSeparator()
        menu.addAction(self.loc.get("export_settings"), self.export_settings_file)
        menu.addAction(self.loc.get("import_settings"), self.import_settings_file)
        menu.addSeparator()
        menu.addAction(self.loc.get("exit_menu"), QApplication.instance().quit)
        menu.exec(self.mapToGlobal(pos))
    
    def show_main_popup(self, note_to_select=None):
        if self.main_popup is None:
            self.main_popup = MainPopup(self)
            self.main_popup.animation_finished_and_hidden.connect(self.on_popup_closed)
            self.main_popup.notes_panel.note_created.connect(self.on_note_created_in_cache)
        
        # ИЗМЕНЕНИЕ: Всегда перезагружаем данные при открытии
        self.reload_from_disk(self.main_popup)
        
        if note_to_select:
            self.main_popup.notes_panel.find_and_select_note_by_timestamp(note_to_select)

        self.main_popup.retranslate_ui()
        self.main_popup.apply_theme(self.settings)
        pos = self.settings.get("trigger_pos", "right")
        screen = QApplication.primaryScreen().availableGeometry()
        popup_x = self.width() if pos == "left" else screen.width() - 380
        player_pos = QPoint(popup_x, screen.y())
        self.main_popup.show_animated(player_pos, from_left=(pos == "left"))

    def _on_main_window_splitter_moved(self, sizes):
        """Обновляет значения в панели настроек, если она открыта."""
        if self.main_window and self.main_window.settings_panel_main.isVisible():
            # Этот метод нужно будет добавить в SettingsPanel
            self.main_window.settings_panel_main.update_splitter_values(sizes)

    def show_main_window(self, note_to_select=None):
        if self.main_window is None:
            self.note_to_select_after_load = note_to_select
            self.main_window = WindowMain(self)
            self.main_window.window_closed.connect(self.on_window_closed)
            self.main_window.splitter_sizes_changed.connect(self._on_main_window_splitter_moved)
        
        # ИЗМЕНЕНИЕ: Всегда перезагружаем данные при открытии
        self.reload_from_disk(self.main_window)

        self.main_window.retranslate_ui()
        self.main_window.apply_theme(self.settings)
        
        if hasattr(self.main_window, "set_tree_enabled"):
            self.main_window.set_tree_enabled(True)
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def switch_to_window_mode(self):
        if self.main_popup and self.main_popup.isVisible():
            self.note_to_select_after_load = self._get_current_note_ts(self.main_popup)
            self.is_switching_to_window = True
            self.save_app_data()
            self.main_popup.close()
        else:
            self.show_main_window(note_to_select=self.note_to_select_after_load)
    
    def on_note_created_in_cache(self, timestamp: str):
        if not timestamp: return
        root_folder = self._find_folder_node(self.note_tree_cache, self.notes_root_folder)
        if root_folder is None:
            root_folder = {"type": "folder", "name": self.notes_root_folder, "children": []}
            self.note_tree_cache.insert(0, root_folder)
        if timestamp not in self._collect_tree_timestamps([root_folder]):
            root_folder.setdefault("children", []).append({"type": "note", "timestamp": timestamp})

    def switch_to_popup_from_window(self):
        ts = self._get_current_note_ts(self.main_window) if self.main_window else None
        self.save_app_data()
        if self.main_window:
            self.main_window.close()
        self.show_main_popup(note_to_select=ts)

    # ЗАМЕНИТЬ в классе TriggerButton
    def enter_zen_mode(self, initial_text, timestamp):
            # Перед входом в Zen сохраняем текущее состояние UI
        self.save_app_data() 
        self.pending_zen_data = (initial_text, timestamp)
        self.zen_source_timestamp = timestamp
        self.is_entering_zen = True
            
            # Запоминаем, в какой режим возвращаться
        if self.main_window and self.main_window.isVisible():
            self.zen_return_to_window_mode = True
        else:
            self.zen_return_to_window_mode = False

            # Закрываем активное окно, что запустит цепочку событий
        if active_ui := self._choose_ui():
            active_ui.close()
        else:
                # Если ни одно окно не было открыто (маловероятно), запускаем вручную
            self.on_popup_closed() 

    # ЗАМЕНИТЬ в классе TriggerButton
    def on_window_closed(self):
        if self.main_window:
            self.main_window.deleteLater()
            self.main_window = None

        if self.is_entering_zen:
            self._launch_zen_window()

    def on_popup_closed(self):
        if self.is_switching_to_window:
            self.is_switching_to_window = False
            self.show_main_window(note_to_select=self.note_to_select_after_load)
            return

        if self.is_entering_zen:
            self._launch_zen_window()

        # ДОБАВИТЬ НОВЫЙ МЕТОД в класс TriggerButton
    def _launch_zen_window(self):
        if self.pending_zen_data is None:
            self.is_entering_zen = False
            return
            
        initial_text, timestamp = self.pending_zen_data
        self.is_entering_zen = False
        self.pending_zen_data = None
        
        self.hide() # Скрываем триггер-кнопку
        self.zen_window = ZenModeWindow(initial_text, self.get_settings(), self.loc, self)
        try:
            self.zen_window.attach_global_audio_widget(self.global_audio, self.loc)
        except Exception:
            pass
            
        self.zen_window.zen_exited.connect(lambda text: self.handle_zen_exit(text, False))
        self.zen_window.zen_saved_and_closed.connect(lambda text: self.handle_zen_exit(text, True))
        self.zen_window.showFullScreen()

    # ЗАМЕНИТЬ в классе TriggerButton
    def handle_zen_exit(self, text_from_zen, should_clear):
        if self.zen_window:
            self.zen_window.close()
            self.zen_window = None
        
        # 1. Сначала сохраняем все изменения на диск.
        self.save_zen_note(self.zen_source_timestamp, text_from_zen)
        
        # 2. Показываем триггер-кнопку.
        self.show()
        
        # 3. Определяем, какую заметку выделить.
        note_to_select = None if should_clear else self.zen_source_timestamp
        
        # 4. Открываем нужное окно. Оно само загрузит свежие данные с диска.
        if self.zen_return_to_window_mode:
            self.show_main_window(note_to_select=note_to_select)
        else:
            self.show_main_popup(note_to_select=note_to_select)


    def update_settings(self, new_settings):
        self.settings = new_settings
        self.save_settings()
        self.update_position_and_style()
        
        if self.main_popup: 
            self.main_popup.apply_theme(new_settings)
            self.main_popup.retranslate_ui() # Дополнительный вызов для обновления
        if self.main_window: 
            self.main_window.apply_theme(new_settings)
            self.main_window.retranslate_ui() # Обновляем заголовок
        if self.zen_window: 
            self.zen_window.update_zen_settings(new_settings)
            
        # Мгновенно переводим панель настроек
        if active_ui := self._choose_ui():
            if hasattr(active_ui, 'settings_panel_main') and active_ui.settings_panel_main.isVisible():
                active_ui.settings_panel_main.retranslate_ui()
        
        self.settings_changed.emit(self.settings)

    def create_backup(self):
        # Сохраняем актуальные данные перед бэкапом
        self.save_app_data()
        
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        if os.path.exists(DATA_FILE):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"data_{timestamp}.bak")
            try:
                # ИЗМЕНЕНИЕ: Копируем основной файл данных, который уже содержит все структуры
                shutil.copyfile(DATA_FILE, backup_path)
                print(f"Резервная копия создана: {backup_path}")
                QMessageBox.information(self, "Бэкап", f"Резервная копия успешно создана!")
            except Exception as e:
                print(f"Не удалось создать резервную копию: {e}")

    def restore_from_backup(self):
        dialog = BackupManagerDialog(self, self.loc)
        if dialog.exec():
            selected_file = dialog.selected_backup
            if not selected_file:
                return

            reply = QMessageBox.question(self, self.loc.get("restore_menu"), self.loc.get("backup_confirm_restore").format(date=dialog.get_date_from_filename(selected_file)))
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    shutil.copyfile(selected_file, DATA_FILE)
                    
                    # ИЗМЕНЕНИЕ: Принудительно перезагружаем данные в активное окно
                    if ui := self._choose_ui():
                        self.reload_from_disk(ui)
                    
                    QMessageBox.information(self, "Успех", "Данные восстановлены.")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось восстановить: {e}")

    def export_notes_to_markdown(self):
        self.save_app_data()
        notes_map = {note['timestamp']: note for note in self.all_notes_cache}
        if not notes_map:
            QMessageBox.information(self, "Информация", "Нет заметок для экспорта.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт заметок", "Мои_заметки.md", "Markdown Files (*.md);;Text Files (*.txt)")
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("# Экспорт заметок\n\n")
                def traverse_and_write(nodes, path_prefix):
                    for node in nodes:
                        if node.get("type") == "folder":
                            new_prefix = f"{path_prefix}{node.get('name', 'Без имени')} / "
                            traverse_and_write(node.get("children", []), new_prefix)
                        elif node.get("type") == "note":
                            ts = node.get("timestamp")
                            if note_data := notes_map.get(ts):
                                f.write(f"## [Путь: {path_prefix.strip(' /')}] Заметка от: {ts}\n\n")
                                f.write(f"{note_data.get('text', '')}\n\n---\n\n")
                traverse_and_write(self.note_tree_cache, "")
            QMessageBox.information(self, "Успех", f"Заметки экспортированы в {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {e}")

    def export_settings_file(self):
        path, _ = QFileDialog.getSaveFileName(self, self.loc.get("export_settings"), "settings_export.json", "JSON (*.json)")
        if not path: return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "OK", f"Настройки экспортированы в {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {e}")

    def import_settings_file(self):
        path, _ = QFileDialog.getOpenFileName(self, self.loc.get("import_settings"), "", "JSON (*.json)")
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                incoming = json.load(f)
            new_settings = DEFAULT_SETTINGS.copy()
            new_settings.update(self.settings)
            new_settings.update(incoming)
            self.update_settings(new_settings)
            QMessageBox.information(self, "OK", "Настройки импортированы")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать: {e}")

    def show_about_dialog(self):
        if self.about_dialog is None:
            self.about_dialog = AboutDialog(self)
        screen = self.screen().geometry() if self.screen() else QApplication.primaryScreen().geometry()
        self.about_dialog.retranslate_ui()
        dlg_size = self.about_dialog.size()
        x = screen.x() + (screen.width() - dlg_size.width()) // 2
        y = screen.y() + (screen.height() - dlg_size.height()) // 2
        self.about_dialog.move(x, y)
        self.about_dialog.exec()

    def _create_default_data(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        welcome_note = {"timestamp": now, "text": "Добро пожаловать!", "pinned": True}
        return {
            "task_lists": {"Default": []}, "active_task_list": "Default",
            "notes": [welcome_note],
            "note_tree": [{"type": "folder", "name": self.notes_root_folder, "children": [{"type": "note", "timestamp": now}]}]
        }

    def _load_and_validate_data(self):
        data_changed = False
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = self._create_default_data()
            data_changed = True
        
        if "notes" not in data or not isinstance(data["notes"], list):
            data["notes"] = []
            data_changed = True
        if "note_tree" not in data or not isinstance(data["note_tree"], list):
            data["note_tree"] = []
            data_changed = True
        if "task_lists" not in data:
            data["task_lists"] = {"Default": []}
            data_changed = True
        if not self._find_folder_node(data["note_tree"], self.notes_root_folder):
            data["note_tree"].insert(0, {"type": "folder", "name": self.notes_root_folder, "children": []})
            data_changed = True
        
        if self._dedupe_notes_and_fix_tree(data): data_changed = True
        
        if data_changed:
            try:
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"Error saving validated data: {e}")
                
        self.all_notes_cache = data.get("notes", [])
        self.note_tree_cache = self._reconcile_note_tree_with_notes(data.get("note_tree", []), self.all_notes_cache)

    def reload_from_disk(self, container):
        self._load_and_validate_data()
        self._update_ui_from_cache(container)

    def _update_ui_from_cache(self, container):
        if not container: return
        try:
             with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
            
        task_lists = data.get("task_lists", {})
        active_list = data.get("active_task_list", "Default")
        container.tasks_panel.load_task_lists(task_lists, active_list)
        
        notes_panel = container.notes_panel
        notes_panel.note_list_widget.blockSignals(True)
        try:
            if isinstance(container, MainPopup):
                folder = self._find_folder_node(self.note_tree_cache, self.notes_root_folder) or {"children": []}
                allowed_ts = self._collect_tree_timestamps([folder])
                notes_to_show = [n for n in self.all_notes_cache if n.get("timestamp") in allowed_ts]
                notes_panel.load_notes(notes_to_show)
            else:
                notes_panel.load_notes(self.all_notes_cache)
                if hasattr(container, "load_note_tree"):
                    container.load_note_tree(self.note_tree_cache)
            
            if self.note_to_select_after_load:
                notes_panel.find_and_select_note_by_timestamp(self.note_to_select_after_load)
                self.note_to_select_after_load = None
        finally:
            notes_panel.note_list_widget.blockSignals(False)
            if notes_panel.note_list_widget.currentItem():
                notes_panel.display_selected_note(notes_panel.note_list_widget.currentItem(), None)
            else:
                notes_panel.clear_for_new_note(force=True)
                
        if container.isVisible():
            container.set_status_saved()

    def _collect_tree_timestamps(self, tree_list):
        out = set()
        for node in tree_list or []:
            if node.get("type") == "note":
                if ts := node.get("timestamp"):
                    out.add(ts)
            elif node.get("type") == "folder":
                out |= self._collect_tree_timestamps(node.get("children", []))
        return out

    def _filter_tree_by_valid_ts(self, tree_list, valid_ts_set):
        result = []
        for node in tree_list or []:
            if node.get("type") == "note":
                if node.get("timestamp") in valid_ts_set:
                    result.append(node)
            elif node.get("type") == "folder":
                new_children = self._filter_tree_by_valid_ts(node.get("children", []), valid_ts_set)
                nd = dict(node)
                nd["children"] = new_children
                result.append(nd)
        return result

    def _find_folder_node(self, tree_list, name):
        for node in tree_list or []:
            if node.get("type") == "folder" and node.get("name") == name:
                return node
            if "children" in node:
                if found := self._find_folder_node(node["children"], name):
                    return found
        return None

    def _add_ts_list_into_folder(self, tree_list, folder_name, missing_ts):
        folder = self._find_folder_node(tree_list, folder_name)
        if folder is None:
            folder = {"type": "folder", "name": folder_name, "children": []}
            tree_list.insert(0, folder)
        existing = self._collect_tree_timestamps([folder])
        for ts in missing_ts:
            if ts not in existing:
                folder.setdefault("children", []).append({"type": "note", "timestamp": ts})
            
    def _reconcile_note_tree_with_notes(self, tree_list, notes):
        valid_ts = {n.get("timestamp") for n in notes if n.get("timestamp")}
        filtered_tree = self._filter_tree_by_valid_ts(tree_list or [], valid_ts)
        present_ts_in_tree = self._collect_tree_timestamps(filtered_tree)
        missing_ts = valid_ts - present_ts_in_tree
        if missing_ts:
            self._add_ts_list_into_folder(filtered_tree, self.notes_root_folder, missing_ts)
        return filtered_tree

    def _dedupe_notes_and_fix_tree(self, data) -> bool:
        notes = data.get("notes", [])
        tree = data.get("note_tree", [])
        seen = set()
        remap = {}
        changed = False
        unique_notes = []
        for n in notes:
            ts = n.get("timestamp") or ""
            if not ts or ts in seen:
                new_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                while new_ts in seen:
                    new_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                if ts: remap[ts] = new_ts
                n["timestamp"] = new_ts
                seen.add(new_ts)
                changed = True
            else:
                seen.add(ts)
            unique_notes.append(n)
        if changed:
            def fix_tree_timestamps(nodes):
                for node in nodes or []:
                    if node.get("type") == "note":
                        if (ts := node.get("timestamp")) in remap:
                            node["timestamp"] = remap[ts]
                    elif node.get("type") == "folder":
                        fix_tree_timestamps(node.get("children", []))
            fix_tree_timestamps(tree)
            data["notes"] = unique_notes
            data["note_tree"] = tree
        return changed

    def save_app_data(self, force_container=None):
        container = force_container or self._choose_ui()
        if not container:
            return

        data_to_save = {}
        try:
            if isinstance(container, QWidget) and not container.isWidgetType(): return
            
            # Собираем данные из активного окна
            tasks_data = container.tasks_panel.get_task_lists_data()
            active_task_list = container.tasks_panel.current_list_name
            
            # Обновляем кеш заметок данными из редактора
            ui_notes = container.notes_panel.get_notes_data()
            all_notes_dict = {n['timestamp']: n for n in self.all_notes_cache}
            for note in ui_notes:
                if note.get("timestamp"):
                    all_notes_dict[note['timestamp']] = note
            self.all_notes_cache = list(all_notes_dict.values())

            # Дерево берем из WindowMain, если он активен, иначе из кеша
            if isinstance(container, WindowMain):
                self.note_tree_cache = container.get_note_tree_data()

            data_to_save = {
                "task_lists": tasks_data,
                "active_task_list": active_task_list,
                "notes": self.all_notes_cache,
                "note_tree": self.note_tree_cache,
            }
        except RuntimeError as e:
            print(f"Ошибка при сборе данных для сохранения: {e}.")
            return

        final_tree = self._reconcile_note_tree_with_notes(data_to_save.get("note_tree", []), data_to_save.get("notes", []))
        data_to_save["note_tree"] = final_tree
        
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            if container.isVisible():
                container.set_status_saved()
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")

    def delete_note_by_timestamp_from_all_data(self, timestamp: str):
        if not timestamp: return
        self.all_notes_cache = [note for note in self.all_notes_cache if note.get("timestamp") != timestamp]
        def find_and_remove_in_tree(nodes):
            nodes[:] = [node for node in nodes if not (node.get("type") == "note" and node.get("timestamp") == timestamp)]
            for node in nodes:
                if node.get("type") == "folder":
                    find_and_remove_in_tree(node.get("children", []))
        find_and_remove_in_tree(self.note_tree_cache)
        self.save_app_data()

    # В классе TriggerButton

        # ЗАМЕНИТЬ в классе TriggerButton
    def save_zen_note(self, note_timestamp, new_text):
        """
        Обновляет или создает заметку в кеше и СРАЗУ ЖЕ сохраняет все данные на диск.
        Это централизует сохранение после выхода из Zen.
        """
        if not new_text.strip() and not note_timestamp:
            return

        note_found = False
        if note_timestamp:
            # Ищем заметку в кеше и обновляем ее
            for note in self.all_notes_cache:
                if note.get("timestamp") == note_timestamp:
                    note["text"] = new_text
                    note_found = True
                    break
        
        if not note_found:
            # Если заметка не найдена (была новая), создаем ее
            new_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            new_note = {"timestamp": new_timestamp, "text": new_text, "pinned": False}
            self.all_notes_cache.append(new_note)
            # Обновляем timestamp, чтобы после выхода из Zen выделилась новая заметка
            self.zen_source_timestamp = new_timestamp 
            # Добавляем новую заметку в дерево
            self.on_note_created_in_cache(new_timestamp)

        # --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ ---
        # Собираем все текущие данные из кеша и сохраняем их на диск.
        # Мы не полагаемся на UI, так как его еще нет или он закрывается.
        # --- ПРАВИЛЬНЫЙ БЛОК ---
        data_to_save = {
            "notes": self.all_notes_cache,
            "note_tree": self.note_tree_cache,
            # Данные по задачам просто берем из кеша, как они были до входа в Zen.
            # Это безопасно, так как в Zen мы их не меняем.
            "task_lists": self.main_popup.tasks_panel.get_task_lists_data() if self.main_popup else {},
            "active_task_list": self.main_popup.tasks_panel.current_list_name if self.main_popup else "Default"
        }

        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            print("Data saved successfully after Zen mode.")
        except Exception as e:
            print(f"Ошибка сохранения данных после Zen: {e}")


    def main_popup_on_data_changed(self):
        container = self._choose_ui()
        if not container: return
        try:
            is_dirty = getattr(container.notes_panel, "is_dirty", False)
            if isinstance(container, WindowMain) and container.current_edit_target and container.current_edit_target[0] == "folder":
                is_dirty = container.notes_panel.notes_editor.toPlainText() != container.notes_panel.saved_text
            if is_dirty:
                container.on_data_changed()
            else:
                container.set_status_saved()
        except Exception as e:
            print(f"main_popup_on_data_changed: {e}")

class BackupManagerDialog(QDialog):
    def __init__(self, parent, loc):
        super().__init__(parent)
        self.loc = loc
        self.setWindowTitle(self.loc.get("backup_manager_title"))
        self.setMinimumSize(400, 300)
        
        self.selected_backup = None
        
        layout = QVBoxLayout(self)
        info_label = QLabel(self.loc.get("backup_available_copies"))
        self.backup_list_widget = QListWidget()
        
        button_layout = QHBoxLayout()
        self.restore_button = QPushButton(self.loc.get("backup_restore_btn"))
        self.delete_button = QPushButton(self.loc.get("backup_delete_btn"))
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addStretch()
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addWidget(info_label)
        layout.addWidget(self.backup_list_widget)
        layout.addLayout(button_layout)
        
        self.restore_button.clicked.connect(self.accept)
        self.delete_button.clicked.connect(self.delete_selected)
        self.cancel_button.clicked.connect(self.reject)
        
        self.backup_list_widget.itemSelectionChanged.connect(self.update_button_states)
        self.backup_list_widget.itemDoubleClicked.connect(self.accept)

        self.populate_backups()
        self.update_button_states()
        
        # Применяем тему
        settings = parent.get_settings() if hasattr(parent, 'get_settings') else {}
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; }}
            QLabel {{ color: {text}; }}
            QListWidget {{
                background-color: {comp_bg}; border: 1px solid {border};
                color: {text}; border-radius: 4px;
            }}
            QListWidget::item:selected {{ background-color: {accent}; }}
            QPushButton {{
                background-color: {comp_bg}; color: {text}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 4px; min-width: 80px;
            }}
            QPushButton:hover {{ border-color: {accent}; }}
        """)


    def populate_backups(self):
        self.backup_list_widget.clear()
        if not os.path.exists(BACKUP_DIR):
            self.backup_list_widget.addItem(self.loc.get("backup_no_copies"))
            return
            
        backups = sorted(glob(os.path.join(BACKUP_DIR, "data_*.bak")), reverse=True)
        if not backups:
            self.backup_list_widget.addItem(self.loc.get("backup_no_copies"))
            return
            
        for backup_file in backups:
            item_text = self.get_date_from_filename(backup_file)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, backup_file)
            self.backup_list_widget.addItem(item)
    
    def get_date_from_filename(self, filename):
        try:
            timestamp_str = os.path.basename(filename).replace("data_", "").replace(".bak", "")
            dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return os.path.basename(filename)

    def update_button_states(self):
        has_selection = bool(self.backup_list_widget.selectedItems())
        self.restore_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        
    def accept(self):
        if self.backup_list_widget.selectedItems():
            self.selected_backup = self.backup_list_widget.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
            super().accept()
        
    def delete_selected(self):
        if not self.backup_list_widget.selectedItems():
            return
            
        item = self.backup_list_widget.selectedItems()[0]
        file_path = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, self.loc.get("delete_note_tooltip"), 
                                     self.loc.get("backup_confirm_delete"))
                                     
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(file_path)
                self.populate_backups()
                self.update_button_states()
            except OSError as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить файл: {e}")

class ThemedIconProvider:
    SVG = {
        "play":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M8 5v14l11-7z'/></svg>", "pause":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M6 5h5v14H6V5zm7 0h5v14h-5V5z'/></svg>",
        "stop":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M6 6h12v12H6z'/></svg>", "prev":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M6 6h2v12H6zM9 12l9 6V6z'/></svg>",
        "next":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M16 6h2v12h-2zM6 18l9-6-9-6z'/></svg>", "chev_l":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12z'/></svg>",
        "chev_r": "<svg viewBox='0 0 24 24'><path fill='{c}' d='M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z'/></svg>",
        "add_file":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8m-6-6v6h6M11 10v3H8v2h3v3h2v-3h3v-2h-3v-3z'/></svg>",
        "add_folder":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M10 4H4a2 2 0 0 0-2 2v2h20V8a2 2 0 0 0-2-2h-8l-2-2m-8 6v8a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-8H2m10 2h2v3h3v2h-3v3h-2v-3H9v-2h3v-3z'/></svg>",
        "trash":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M9 3v1H4v2h16V4h-5V3H9m-3 6v11a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V9H6Z'/></svg>",
        "volume":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M5 9v6h4l5 4V5L9 9H5m12.5 3a4.5 4.5 0 0 0-3-4.24v8.48c1.76-.62 3-2.29 3-4.24Z'/></svg>",
        "volume_mute":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M12 4.44 9.77 6.67 12 8.9V4.44M4.27 3 3 4.27l6 6V14H3v-4H0v4h3v5h5l4 4V17.9l4.73 4.73L21 21.73 4.27 3M19 12a7 7 0 0 0-5-6.71v2.06A5 5 0 0 1 17 12a5 5 0 0 1-1 3l1.45 1.45A7 7 0 0 0 19 12Z'/></svg>",
        "gear":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M12 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7ZM19.43 12.98c.04-.32.07-.65.07-.98s-.03-.66-.07-.98l2.11-1.65a.5.5 0 0 0 .12-.64l-2-3.46a.5.5 0 0 0-.6-.22l-2.49 1a7.05 7.05 0 0 0-1.7-.98l-.38-2.65A.5.5 0 0 0 12 1h-4a.5.5 0 0 0-.5.42l-.38 2.65a7.05 7.05 0 0 0-1.7-.98l-2.49-1a.5.5 0 0 0-.6.22l-2 3.46a.5.5 0 0 0 .12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98L.96 14.62a.5.5 0 0 0-.12.64l2 3.46a.5.5 0 0 0 .6.22l2.49-1c.52.4 1.09.73 1.7.98l.38 2.65A.5.5 0 0 0 8 23h4a.5.5 0 0 0 .5-.42l.38-2.65c.61-.25 1.18-.58 1.7-.98l2.49 1a.5.5 0 0 0 .6-.22l2-3.46a.5.5 0 0 0-.12-.64l-2.11-1.64Z'/></svg>",
        "window":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm1 3h14v9H5V8Z'/></svg>",
        "note":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6Z'/></svg>",
        "close":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12Z'/></svg>",
        "folder":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2z'/></svg>",
        "file":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z M13 9V3.5L18.5 9H13z'/></svg>",
        "pin":"<svg viewBox='0 0 24 24'><path fill='{c}' d='M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z'/></svg>",
    }
    @staticmethod
    def icon(name: str, settings: dict, size: QSize = QSize(18, 18)) -> QIcon:
        svg = ThemedIconProvider.SVG.get(name)
        if not svg: return QIcon()
        is_dark = settings.get("theme") == "dark"
        color = settings.get("dark_theme_text") if is_dark else settings.get("light_theme_text")
        data = svg.replace("{c}", color)
        renderer = QSvgRenderer(bytearray(data, encoding="utf-8"))
        pm = QPixmap(size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        renderer.render(p)
        p.end()
        return QIcon(pm)

# --- Точка входа ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    loc_manager = LocalizationManager()

    def _excepthook(exctype, value, tb):
        import traceback
        msg = "".join(traceback.format_exception(exctype, value, tb))
        print(msg)
        try:
            QMessageBox.critical(None, "Критическая ошибка", f"Произошла непредвиденная ошибка:\n\n{msg}\n\nПриложение может работать нестабильно.")
        except Exception:
            pass
    sys.excepthook = _excepthook
    
    trigger = TriggerButton(loc_manager)
    
    def update_global_dialog_stylesheet():
        settings = trigger.get_settings()
        is_dark, accent, bg, text, _ = theme_colors(settings)
        comp_bg = QColor(bg).lighter(115).name() if is_dark else QColor(bg).darker(105).name()
        border = "#555" if is_dark else "#ced4da"
        
        dialog_stylesheet = f"""
            QDialog, QMessageBox, QInputDialog {{
                background-color: {bg};
            }}
            QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {{
                color: {text};
                background-color: transparent;
            }}
            QDialog QLineEdit, QMessageBox QLineEdit, QInputDialog QLineEdit {{
                background-color: {comp_bg};
                border: 1px solid {border};
                border-radius: 4px;
                color: {text};
                padding: 5px;
                min-width: 200px;
            }}
            QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton {{
                background-color: {comp_bg};
                color: {text};
                border: 1px solid {border};
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 80px;
                min-height: 20px;
            }}
            QDialog QPushButton:hover, QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {{
                background-color: {QColor(comp_bg).lighter(110).name()};
                border: 1px solid {accent};
            }}
            QDialog QPushButton:pressed, QMessageBox QPushButton:pressed, QInputDialog QPushButton:pressed {{
                background-color: {QColor(comp_bg).darker(105).name()};
            }}
            QDialogButtonBox {{
                dialogbuttonbox-buttons-have-icons: 0;
            }}
        """
        app.setStyleSheet(dialog_stylesheet)

    update_global_dialog_stylesheet()
    trigger.settings_changed.connect(update_global_dialog_stylesheet)
    
    trigger.show()
    sys.exit(app.exec())