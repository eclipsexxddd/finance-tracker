import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QDialog
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from pathlib import Path

from app.db import init_db, get_balance, get_transactions, get_expenses_by_category, add_transaction, delete_transaction, clear_database
from app.dialogs import TransactionDialog, CategoryDialog
from app.utils import export_csv, import_csv

# matplotlib integration
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class PieCanvas(FigureCanvas):
    def __init__(self, parent=None, width=4, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)

    def plot(self, data):
        self.ax.clear()
        if not data:
            self.ax.text(0.5, 0.5, 'Нет данных', ha='center')
            self.draw()
            return
        labels = [d['name'] for d in data]
        sizes = [d['total'] for d in data]
        self.ax.pie(sizes, labels=labels, autopct='%1.1f%%')
        self.ax.axis('equal')
        self.draw()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(resource_path("images/app_icon.png")))
        self.setWindowTitle('Finance Tracker')
        self.resize(900,600)
        init_db()

        central = QWidget()
        layout = QVBoxLayout()

        top = QHBoxLayout()
        self.balance_label = QLabel('Баланс: 0.00')
        top.addWidget(self.balance_label)
        top.addStretch()
        add_btn = QPushButton('Добавить')
        add_btn.clicked.connect(self.add_transaction)
        cat_btn = QPushButton('Категории')
        cat_btn.clicked.connect(self.add_category)
        imp_btn = QPushButton('Импорт CSV')
        imp_btn.clicked.connect(self.import_csv)
        exp_btn = QPushButton('Экспорт CSV')
        exp_btn.clicked.connect(self.export_csv)
        clear_db_btn = QPushButton('Очистить')
        clear_db_btn.clicked.connect(self.clear_database_dialog)
        top.addWidget(clear_db_btn)
        top.addWidget(add_btn)
        top.addWidget(cat_btn)
        top.addWidget(imp_btn)
        top.addWidget(exp_btn)

        layout.addLayout(top)

        mid = QHBoxLayout()
        self.table = QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(['ID','Дата','Сумма','Тип','Категория','Примечание'])
        self.table.setColumnHidden(0, True)
        self.table.cellDoubleClicked.connect(self.edit_transaction)
        mid.addWidget(self.table, 2)

        self.pie = PieCanvas(self, width=4, height=3)
        mid.addWidget(self.pie, 1)

        layout.addLayout(mid)
        central.setLayout(layout)
        self.setCentralWidget(central)

        # контекстное меню
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context)

        self.refresh()

    def refresh(self):
        bal = get_balance()
        self.balance_label.setText(f'Баланс: {bal:.2f}')
        txs = get_transactions()
        self.table.setRowCount(0)
        for r in txs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(r['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(r['date']))
            self.table.setItem(row, 2, QTableWidgetItem(str(r['amount'])))
            self.table.setItem(row, 3, QTableWidgetItem(r['type']))
            # self.table.setItem(row, 4, QTableWidgetItem(r.get('category_name') or ''))
            category_item = QTableWidgetItem()
            name = r.get('category_name') or ''
            icon_path = r.get('category_icon')
            if icon_path:
                from PyQt5.QtGui import QIcon
                category_item.setIcon(QIcon(icon_path))
            category_item.setText(name)
            self.table.setItem(row, 4, category_item)
            self.table.setItem(row, 5, QTableWidgetItem(r.get('note') or ''))

        pie = get_expenses_by_category()
        self.pie.plot(pie)

    def add_transaction(self):
        dlg = TransactionDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            add_transaction(data['date'], data['amount'], data['type'], data['category_id'], data['note'])
            self.refresh()

    def edit_transaction(self, row, col):
        tid = int(self.table.item(row,0).text())
        # получаем полную информацию о транзакции
        txs = get_transactions()
        tx = next((t for t in txs if t['id']==tid), None)
        if not tx:
            return
        from .db import update_transaction
        dlg = TransactionDialog(self, transaction=tx)
        if dlg.exec_() == QDialog.Accepted:
            d = dlg.get_data()
            update_transaction(tid, d['date'], d['amount'], d['type'], d['category_id'], d['note'])
            self.refresh()

    def on_table_context(self, pos):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        sel = self.table.itemAt(pos)
        if not sel:
            return
        row = sel.row()
        tid = int(self.table.item(row,0).text())
        del_action = menu.addAction('Удалить')
        act = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if act == del_action:
            self.confirm_delete(tid)

    def confirm_delete(self, tid):
        ok = QMessageBox.question(self, 'Подтвердите', 'Удалить транзакцию?', QMessageBox.Yes | QMessageBox.No)
        if ok == QMessageBox.Yes:
            delete_transaction(tid)
            self.refresh()

    def add_category(self):
        dlg = CategoryDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.refresh()

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Импорт CSV', '', 'CSV files (*.csv)')
        if path:
            import_csv(path)
            self.refresh()

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Экспорт CSV', '', 'CSV files (*.csv)')
        if path:
            export_csv(path)

    def clear_database_dialog(self):
        reply = QMessageBox.question(
            self,
            'Подтвердите очистку',
            'Внимание! Будут удалены ВСЕ транзакции и категории. \n\nПродолжить?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(
            self,
            'Подтверждение удаления',
            "Для подтверждения введите слово: удалить"
        )

        if not ok:
            return
        if text.strip().lower() != 'удалить':
            QMessageBox.information(self, 'Отмена', 'Неправильное подтверждение. Операция отменена.')
            return

        try:
            clear_database()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'При очистке базы произошла ошибка:\n{e}')
            return

        init_db()  # пересоздаст таблицы, если они были удалены или были пустыми
        QMessageBox.information(self, 'Готово', 'База данных успешно очищена.')
        self.refresh()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())