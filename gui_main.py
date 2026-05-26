import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QCheckBox,
    QTextEdit, QLabel, QLineEdit, QFileDialog
)
from PyQt5.QtCore import Qt
import threading
from concurrent.futures import ThreadPoolExecutor
from login import main  # 导入你的登录主函数

class YibanGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("易班自动签到 v2.0")
        self.setGeometry(300, 300, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 账号表
        self.table = QTableWidget(5, 2)
        self.table.setHorizontalHeaderLabels(["账号", "密码"])
        layout.addWidget(self.table)

        # 任务选项
        task_layout = QVBoxLayout()
        tasks = ["签到", "点赞", "发帖", "评论", "云签到"]
        self.checkboxes = {}
        for task in tasks:
            cb = QCheckBox(task)
            task_layout.addWidget(cb)
            self.checkboxes[task] = cb
        layout.addLayout(task_layout)

        # 运行按钮
        run_btn = QPushButton("运行")
        run_btn.clicked.connect(self.run_task)
        layout.addWidget(run_btn)

        # 日志输出
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def run_task(self):
        self.log_area.append("开始执行任务...")
        accounts = []
        for row in range(self.table.rowCount()):
            account = self.table.item(row, 0).text()
            password = self.table.item(row, 1).text()
            if account and password:
                accounts.append((account, password))

        if not accounts:
            self.log_area.append("未找到有效账号，请添加账号！")
            return

        # 使用 ThreadPoolExecutor 并发处理
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for acc, pwd in accounts:
                future = executor.submit(self._process_account, acc, pwd)
                futures.append(future)

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    self.log_area.append(f"账号 {acc} 失败: {str(e)}")

    def _process_account(self, account, password):
        self.log_area.append(f"正在处理账号: {account}")
        try:
            main(account=account, password=password)
            self.log_area.append(f"✅ 账号 {account} 成功完成任务")
        except Exception as e:
            self.log_area.append(f"❌ 账号 {account} 失败: {str(e)}")