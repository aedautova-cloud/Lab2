import sys
import psycopg2
import logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QMessageBox, QTableWidget, QTableWidgetItem, 
                               QDialog, QFormLayout, QLineEdit, QComboBox, QLabel, QHBoxLayout,
                               QTabWidget, QTextEdit) # <-- Добавили QTabWidget и QTextEdit
from PySide6.QtCore import Qt

# Настройки БД
DB_NAME = "lab1_db"
DB_USER = "postgres"
DB_PASSWORD = "Ali07"  
DB_HOST = "localhost"
DB_PORT = "5432"


SQL_CREATE_SCRIPT = """
CREATE TYPE attack_type_enum AS ENUM ('DDoS', 'BruteForce', 'SQLInjection', 'XSS');
CREATE TABLE models (
    model_id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (model_name, version)
);
CREATE TABLE experiments (
    experiment_id SERIAL PRIMARY KEY,
    model_id INT NOT NULL,
    attack_type attack_type_enum NOT NULL,
    accuracy NUMERIC(5, 2) CHECK (accuracy > 0 AND accuracy <= 100),
    is_successful BOOLEAN DEFAULT FALSE,
    start_time TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_model FOREIGN KEY (model_id) REFERENCES models (model_id) ON DELETE CASCADE ON UPDATE CASCADE
);
"""


# Базовая (из первой лабы)

class TabBasic(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        self.btn_create = QPushButton("Создать схему и таблицы")
        self.btn_create.clicked.connect(self.create_schema)
        self.layout.addWidget(self.btn_create)

        self.btn_insert = QPushButton("Внести данные")
        self.btn_insert.clicked.connect(self.open_insert_dialog)
        self.layout.addWidget(self.btn_insert)

        self.btn_show = QPushButton("Показать данные")
        self.btn_show.clicked.connect(self.show_data)
        self.layout.addWidget(self.btn_show)

        self.layout.addStretch()

    def get_connection(self):
        return psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,  client_encoding='utf8'
            )

    def create_schema(self):
        logging.info("Попытка создания схемы БД (CREATE)")
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(SQL_CREATE_SCRIPT)
            conn.commit()
            cur.close()
            conn.close()
            logging.info("Схема БД успешно создана")
            QMessageBox.information(self, "Успех", "Таблицы успешно созданы!")
        except Exception as e:
            logging.error(f"Ошибка создания схемы: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать таблицы:\n{e}")

    def open_insert_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить эксперимент")
        dialog.setModal(True)
        dialog.resize(400, 300)
        layout = QFormLayout(dialog)
        model_name_edit = QLineEdit()
        version_edit = QLineEdit()
        attack_combo = QComboBox()
        attack_combo.addItems(['DDoS', 'BruteForce', 'SQLInjection', 'XSS'])
        accuracy_edit = QLineEdit()
        accuracy_edit.setPlaceholderText("Например: 95.5")
        layout.addRow("Название модели:", model_name_edit)
        layout.addRow("Версия:", version_edit)
        layout.addRow("Тип атаки:", attack_combo)
        layout.addRow("Точность (%):", accuracy_edit)
        btn_box = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_cancel = QPushButton("Отмена")
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)
        btn_cancel.clicked.connect(dialog.reject)

        def save_data():
            name = model_name_edit.text().strip()
            version = version_edit.text().strip()
            attack = attack_combo.currentText()
            accuracy_text = accuracy_edit.text().strip()
            if not name or not version or not accuracy_text:
                QMessageBox.warning(dialog, "Ошибка", "Все поля обязательны!")
                return
            try:
                accuracy = float(accuracy_text)
            except ValueError:
                QMessageBox.warning(dialog, "Ошибка", "Точность должна быть числом!")
                return
            try:
                conn = self.get_connection()
                cur = conn.cursor()
                cur.execute("SELECT model_id FROM models WHERE model_name = %s AND version = %s;", (name, version))
                result = cur.fetchone()
                if result:
                    model_id = result[0]
                else:
                    cur.execute("INSERT INTO models (model_name, version) VALUES (%s, %s) RETURNING model_id;", (name, version))
                    model_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO experiments (model_id, attack_type, accuracy, is_successful) VALUES (%s, %s, %s, %s);",
                    (model_id, attack, accuracy, accuracy > 90)
                )
                conn.commit()
                cur.close()
                conn.close()
                QMessageBox.information(dialog, "Успех", "Эксперимент добавлен!")
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(dialog, "Ошибка БД", f"Не удалось добавить данные:\n{e}")

        btn_save.clicked.connect(save_data)
        dialog.exec()

    def show_data(self):
        self.data_window = QWidget()
        self.data_window.setWindowTitle("Просмотр экспериментов")
        self.data_window.resize(900, 500)
        layout = QVBoxLayout(self.data_window)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Тип атаки:"))
        self.filter_attack = QComboBox()
        self.filter_attack.addItems(["Все", "DDoS", "BruteForce", "SQLInjection", "XSS"])
        filter_layout.addWidget(self.filter_attack)
        filter_layout.addWidget(QLabel("Успешность:"))
        self.filter_success = QComboBox()
        self.filter_success.addItems(["Все", "Успешные", "Неуспешные"])
        filter_layout.addWidget(self.filter_success)
        self.btn_apply_filter = QPushButton("Применить фильтр")
        self.btn_apply_filter.clicked.connect(self.load_filtered_data)
        filter_layout.addWidget(self.btn_apply_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        self.data_table = QTableWidget()
        layout.addWidget(self.data_table)
        self.load_filtered_data()
        self.data_window.show()

    def load_filtered_data(self):
        attack_filter = self.filter_attack.currentText()
        success_filter = self.filter_success.currentText()
        query = """
            SELECT e.experiment_id, m.model_name, m.version, e.attack_type, e.accuracy, e.is_successful, e.start_time
            FROM experiments e
            JOIN models m ON e.model_id = m.model_id
        """
        conditions = []
        params = []
        if attack_filter != "Все":
            conditions.append("e.attack_type = %s")
            params.append(attack_filter)
        if success_filter == "Успешные":
            conditions.append("e.is_successful = TRUE")
        elif success_filter == "Неуспешные":
            conditions.append("e.is_successful = FALSE")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY e.experiment_id;"
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            headers = ["ID", "Модель", "Версия", "Тип атаки", "Точность", "Успех", "Время"]
            self.data_table.setColumnCount(len(headers))
            self.data_table.setHorizontalHeaderLabels(headers)
            self.data_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    self.data_table.setItem(i, j, QTableWidgetItem(str(value)))
            self.data_table.resizeColumnsToContents()
            cur.close()
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные:\n{e}")


# ALTER TABLE

class TabAlterTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        self.sql_edit = QTextEdit()
        self.sql_edit.setPlaceholderText("Введите SQL-запрос ALTER TABLE, например:\nALTER TABLE models ADD COLUMN description TEXT;")
        
        self.btn_execute = QPushButton("Выполнить ALTER TABLE")
        self.btn_execute.clicked.connect(self.execute_alter)
        
        self.layout.addWidget(QLabel("Введите запрос для изменения структуры БД:"))
        self.layout.addWidget(self.sql_edit)
        self.layout.addWidget(self.btn_execute)
        self.layout.addStretch()

    def execute_alter(self):
        sql = self.sql_edit.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "Ошибка", "Введите SQL-запрос!")
            return
        
        if not sql.upper().startswith("ALTER"):
            QMessageBox.warning(self, "Ошибка", "Запрос должен начинаться с ALTER TABLE!")
            return

        logging.info(f"Попытка ALTER TABLE: {sql}")
        try:
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,client_encoding='utf8' 
            )
            cur = conn.cursor()
            cur.execute(sql)
            conn.commit()
            cur.close()
            conn.close()
            logging.info("ALTER TABLE успешно выполнен")
            QMessageBox.information(self, "Успех", "Структура БД изменена!")
        except Exception as e:
            logging.error(f"Ошибка ALTER TABLE: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить запрос:\n{e}")


# Конструктор SELECT 

class TabSelectBuilder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        #  Блок выбора колонок 
        cols_layout = QHBoxLayout()
        cols_layout.addWidget(QLabel("Колонки (через запятую):"))
        self.cols_edit = QLineEdit()
        self.cols_edit.setPlaceholderText("Например: model_id, model_name, version (или * для всех)")
        self.cols_edit.setText("*")
        cols_layout.addWidget(self.cols_edit)
        self.layout.addLayout(cols_layout)

        #  Блок WHERE 
        where_layout = QHBoxLayout()
        where_layout.addWidget(QLabel("WHERE (условие):"))
        self.where_edit = QLineEdit()
        self.where_edit.setPlaceholderText("Например: model_name LIKE '%Test%'")
        where_layout.addWidget(self.where_edit)
        self.layout.addLayout(where_layout)

        #  Блок GROUP BY 
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("GROUP BY:"))
        self.group_edit = QLineEdit()
        self.group_edit.setPlaceholderText("Например: version")
        group_layout.addWidget(self.group_edit)
        self.layout.addLayout(group_layout)

        #  Блок HAVING 
        having_layout = QHBoxLayout()
        having_layout.addWidget(QLabel("HAVING (для групп):"))
        self.having_edit = QLineEdit()
        self.having_edit.setPlaceholderText("Например: COUNT(*) > 1")
        having_layout.addWidget(self.having_edit)
        self.layout.addLayout(having_layout)

        #  Блок ORDER BY 
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("ORDER BY:"))
        self.order_edit = QLineEdit()
        self.order_edit.setPlaceholderText("Например: model_id ASC")
        order_layout.addWidget(self.order_edit)
        self.layout.addLayout(order_layout)

        #  Блок строковых функций 
        str_layout = QHBoxLayout()
        str_layout.addWidget(QLabel("Строковая функция:"))
        
        self.str_func_combo = QComboBox()
        self.str_func_combo.addItems([
            "Нет", "UPPER", "LOWER", "TRIM", "SUBSTRING", "LPAD", "RPAD", "CONCAT"
        ])
        str_layout.addWidget(self.str_func_combo)

        str_layout.addWidget(QLabel("Применить к колонке:"))
        self.str_col_edit = QLineEdit()
        self.str_col_edit.setPlaceholderText("Например: m.model_name")
        str_layout.addWidget(self.str_col_edit)
        
        self.layout.addLayout(str_layout)

        #  Кнопка и таблица 
        self.btn_execute = QPushButton("Выполнить запрос")
        self.btn_execute.clicked.connect(self.execute_query)
        self.layout.addWidget(self.btn_execute)

        self.result_table = QTableWidget()
        self.layout.addWidget(self.result_table)

    def execute_query(self):
        cols = self.cols_edit.text().strip() or "*"
        
        #  Логика строковых функций 
        func = self.str_func_combo.currentText()
        col_for_func = self.str_col_edit.text().strip()
        
        if func != "Нет" and col_for_func:
            if func in ["UPPER", "LOWER", "TRIM"]:
                new_col = f"{func}({col_for_func}) AS {func.lower()}_result"
            elif func == "SUBSTRING":
                new_col = f"SUBSTRING({col_for_func}, 1, 3) AS substring_result"
            elif func == "LPAD":
                new_col = f"LPAD({col_for_func}::text, 10, '*') AS lpad_result"
            elif func == "RPAD":
                new_col = f"RPAD({col_for_func}::text, 10, '*') AS rpad_result"
            elif func == "CONCAT":
                new_col = f"CONCAT({col_for_func}, ' (ID: ', m.model_id, ')') AS concat_result"
            else:
                new_col = col_for_func
            
            if cols == "*":
                cols = new_col
            else:
                cols = f"{cols}, {new_col}"

        table = "experiments e JOIN models m ON e.model_id = m.model_id"
        query = f"SELECT {cols} FROM {table}"
        
       
        where = self.where_edit.text().strip()
        if where:
            query += f" WHERE {where}"
            
        group = self.group_edit.text().strip()
        if group:
            query += f" GROUP BY {group}"
            
        having = self.having_edit.text().strip()
        if having:
            query += f" HAVING {having}"
            
        order = self.order_edit.text().strip()
        if order:
            query += f" ORDER BY {order}"

        logging.info(f"Выполнение SELECT: {query}")

        try:
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                client_encoding='utf8'
            )
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            
            # Получаем названия колонок из описания курсора
            if cur.description:
                headers = [desc[0] for desc in cur.description]
            else:
                headers = []

            self.result_table.setColumnCount(len(headers))
            self.result_table.setHorizontalHeaderLabels(headers)
            self.result_table.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    self.result_table.setItem(i, j, QTableWidgetItem(str(value)))
            
            self.result_table.resizeColumnsToContents()
            
            cur.close()
            conn.close()
        except Exception as e:
            logging.error(f"Ошибка SELECT: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить запрос:\n{e}")


#  Мастер соединений JOIN 

class TabJoinMaster(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        #  Выбор таблиц 
        table_layout = QHBoxLayout()
        
        table_layout.addWidget(QLabel("Таблица 1:"))
        self.table1_combo = QComboBox()
        self.table1_combo.addItems(["models", "experiments"])
        table_layout.addWidget(self.table1_combo)

        table_layout.addWidget(QLabel("Таблица 2:"))
        self.table2_combo = QComboBox()
        self.table2_combo.addItems(["experiments", "models"])
        self.table2_combo.setCurrentIndex(1)
        table_layout.addWidget(self.table2_combo)
        
        self.layout.addLayout(table_layout)

        #  Тип JOIN 
        join_layout = QHBoxLayout()
        join_layout.addWidget(QLabel("Тип JOIN:"))
        self.join_combo = QComboBox()
        self.join_combo.addItems(["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN"])
        join_layout.addWidget(self.join_combo)
        self.layout.addLayout(join_layout)

        #  Поля для связывания 
        on_layout = QHBoxLayout()
        on_layout.addWidget(QLabel("Поле 1 (ON):"))
        self.on_field1 = QLineEdit()
        self.on_field1.setPlaceholderText("Например: model_id")
        on_layout.addWidget(self.on_field1)

        on_layout.addWidget(QLabel("="))
        
        on_layout.addWidget(QLabel("Поле 2 (ON):"))
        self.on_field2 = QLineEdit()
        self.on_field2.setPlaceholderText("Например: model_id")
        on_layout.addWidget(self.on_field2)
        
        self.layout.addLayout(on_layout)

        #  Кнопка и таблица 
        self.btn_execute = QPushButton("Выполнить JOIN")
        self.btn_execute.clicked.connect(self.execute_join)
        self.layout.addWidget(self.btn_execute)

        self.result_table = QTableWidget()
        self.layout.addWidget(self.result_table)

    def execute_join(self):
        t1 = self.table1_combo.currentText()
        t2 = self.table2_combo.currentText()
        join_type = self.join_combo.currentText()
        f1 = self.on_field1.text().strip()
        f2 = self.on_field2.text().strip()

        if not f1 or not f2:
            QMessageBox.warning(self, "Ошибка", "Укажите поля для связывания (ON)!")
            return

        # Собираем запрос
        query = f"""
            SELECT * 
            FROM {t1} 
            {join_type} {t2} 
            ON {t1}.{f1} = {t2}.{f2};
        """
        
        logging.info(f"Выполнение JOIN: {query}")

        try:
            conn = psycopg2.connect(
                dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT,
                client_encoding='utf8'
            )
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            
            if cur.description:
                headers = [desc[0] for desc in cur.description]
            else:
                headers = []

            self.result_table.setColumnCount(len(headers))
            self.result_table.setHorizontalHeaderLabels(headers)
            self.result_table.setRowCount(len(rows))
            
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    self.result_table.setItem(i, j, QTableWidgetItem(str(value)))
            
            self.result_table.resizeColumnsToContents()
            
            cur.close()
            conn.close()
        except Exception as e:
            logging.error(f"Ошибка JOIN: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить JOIN:\n{e}")
            

# ГЛАВНОЕ ОКНО С ВКЛАДКАМИ

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лабораторная работа №2: ИИ и DDoS")
        self.resize(900, 700)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Добавляем вкладки
        self.tabs.addTab(TabBasic(), "Лаба 1 (Базовая)")
        self.tabs.addTab(TabAlterTable(), "ALTER TABLE")
        self.tabs.addTab(TabSelectBuilder(), "Конструктор SELECT")
        self.tabs.addTab(TabJoinMaster(), "Мастер JOIN")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
