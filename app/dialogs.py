import sys, os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QRadioButton, QTextEdit, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QIcon, QDoubleValidator
from PyQt5.QtCore import QDate
from pathlib import Path
from app.db import get_categories, add_category


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class TransactionDialog(QDialog):
    def __init__(self, parent=None, transaction=None):
        super().__init__(parent)
        self.setWindowTitle('Добавить / Редактировать транзакцию')
        self.transaction = transaction
        layout = QVBoxLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.amount_input = QLineEdit()
        validator = QDoubleValidator(bottom=-1e18, top=1e18, decimals=2, parent=self.amount_input)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(validator)

        self.type_combo = QComboBox()
        self.type_combo.addItems(['Трата', 'Доход'])

        self.category_combo = QComboBox()
        self._load_categories()

        self.note = QTextEdit()

        layout.addWidget(QLabel('Дата'))
        layout.addWidget(self.date_edit)
        layout.addWidget(QLabel('Сумма'))
        layout.addWidget(self.amount_input)
        layout.addWidget(QLabel('Тип'))
        layout.addWidget(self.type_combo)
        layout.addWidget(QLabel('Категория'))
        layout.addWidget(self.category_combo)
        layout.addWidget(QLabel('Примечание'))
        layout.addWidget(self.note)

        btns = QHBoxLayout()
        ok = QPushButton('OK')
        cancel = QPushButton('Отмена')
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)
        self.setLayout(layout)

        if transaction:
            self._fill_from_transaction()

    def _load_categories(self):
        cats = get_categories()
        self.category_map = {c['name']: c['id'] for c in cats}
        self.category_combo.addItem('Без категории', None)
        for c in cats:
            self.category_combo.addItem(c['name'], c['id'])

    def _fill_from_transaction(self):
        t = self.transaction
        # ожидается формат yyyy-MM-dd
        try:
            self.date_edit.setDate(QDate.fromString(t['date'], 'yyyy-MM-dd'))
        except Exception:
            pass
        self.amount_input.setText(str(t['amount']))
        self.type_combo.setCurrentText(t['type'])
        if t.get('category_name'):
            idx = self.category_combo.findText(t['category_name'])
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
        self.note.setPlainText(t.get('note',''))

    def accept(self):
        amt_text = self.amount_input.text().strip()
        amt_text = amt_text.replace(',', '.')
        if amt_text == '':
            QMessageBox.warning(self, 'Ошибка', 'Введите сумму транзакции.')
            return

        try:
            amount = float(amt_text)
        except ValueError:
            QMessageBox.warning(self, 'Ошибка', 'Сумма должна быть числом (например, 123.45).')
            return

        if amount == 0:
            QMessageBox.warning(self, 'Ошибка', 'Сумма не может быть нулевой.')
            return

        if amount < 0:
            QMessageBox.warning(self, 'Ошибка', 'Введите положительную сумму.')
            return

        super().accept()

    def get_data(self):
        date = self.date_edit.date().toString('yyyy-MM-dd')
        amt_text = self.amount_input.text().strip().replace(',', '.')
        amount = float(amt_text) if amt_text else 0.0
        ttype = self.type_combo.currentText()
        cat_id = self.category_combo.currentData()
        note = self.note.toPlainText()
        return dict(date=date, amount=amount, type=ttype, category_id=cat_id, note=note)


class CategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Добавить категорию')
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        layout.addWidget(QLabel('Название'))
        layout.addWidget(self.name_input)

        # выпадающий список с иконками
        layout.addWidget(QLabel('Иконка (необязательно)'))
        self.icon_combo = QComboBox()
        self._load_icons()
        layout.addWidget(self.icon_combo)

        # кнопки управления
        btns = QHBoxLayout()
        save = QPushButton('Сохранить')
        cancel = QPushButton('Отмена')
        save.clicked.connect(self.save)
        cancel.clicked.connect(self.reject)
        btns.addWidget(save)
        btns.addWidget(cancel)
        layout.addLayout(btns)

        self.setLayout(layout)

    def _load_icons(self):
        icons_path = resource_path("images")
        self.icon_combo.addItem('Без иконки', userData=None)

        if not os.path.exists(icons_path):
            return

        for file_name in os.listdir(icons_path):
            if file_name.lower().endswith((".png")):
                icon_path = os.path.join(icons_path, file_name)
                icon = QIcon(icon_path)
                name = os.path.splitext(file_name)[0].replace('_', ' ').title()
                self.icon_combo.addItem(icon, name, userData=icon_path)

    def save(self):
        name = self.name_input.text().strip()
        icon_path = self.icon_combo.currentData()  # путь к выбранной иконке
        if not name:
            QMessageBox.warning(self, 'Ошибка', 'Введите имя категории')
            return
        add_category(name, icon_path)
        self.accept()