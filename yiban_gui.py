import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import time
import os

class YibanGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("智慧内师学工系统")
        self.root.geometry("1000x700")
        
        # 初始化变量
        self.accounts = []
        self.selected_account = None
        self.functions = {
            'check_in': False,
            'like': False,
            'post': False,
            'comment': False
        }
        self.running_threads = []
        
        # 加载账号数据
        self.load_accounts()
        
        # 创建GUI组件
        self.create_widgets()
    
    def load_accounts(self):
        """从accounts.json文件加载账号数据"""
        try:
            with open('accounts.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.accounts = data.get('accounts', [])
        except FileNotFoundError:
            print("accounts.json文件未找到，使用默认账号")
            self.accounts = [
                {'id': '1', 'username': 'default_user'},
                {'id': '2', 'username': 'default_user2'}
            ]
        except Exception as e:
            print(f"加载账号数据时出错: {e}")
            self.accounts = []
    
    def create_widgets(self):
        """创建所有GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # 左上：账号信息
        account_frame = ttk.LabelFrame(main_frame, text="账号信息", padding="10")
        account_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 账号选择下拉框
        ttk.Label(account_frame, text="账号1:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.account_var1 = tk.StringVar()
        self.account_combo1 = ttk.Combobox(account_frame, textvariable=self.account_var1, width=20)
        self.account_combo1['values'] = [acc['username'] for acc in self.accounts]
        self.account_combo1.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(account_frame, text="账号2:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.account_var2 = tk.StringVar()
        self.account_combo2 = ttk.Combobox(account_frame, textvariable=self.account_var2, width=20)
        self.account_combo2['values'] = [acc['username'] for acc in self.accounts]
        self.account_combo2.grid(row=1, column=1, padx=5, pady=5)
        
        # 右上：功能选择
        function_frame = ttk.LabelFrame(main_frame, text="功能选择", padding="10")
        function_frame.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 功能复选框
        self.check_in_var = tk.BooleanVar()
        self.check_in_checkbox = ttk.Checkbutton(function_frame, text="签到", variable=self.check_in_var)
        self.check_in_checkbox.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.like_var = tk.BooleanVar()
        self.like_checkbox = ttk.Checkbutton(function_frame, text="点赞", variable=self.like_var)
        self.like_checkbox.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.post_var = tk.BooleanVar()
        self.post_checkbox = ttk.Checkbutton(function_frame, text="发帖", variable=self.post_var)
        self.post_checkbox.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.comment_var = tk.BooleanVar()
        self.comment_checkbox = ttk.Checkbutton(function_frame, text="评论", variable=self.comment_var)
        self.comment_checkbox.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 执行按钮
        self.execute_btn = ttk.Button(function_frame, text="执行", command=self.execute_tasks)
        self.execute_btn.grid(row=4, column=0, padx=5, pady=10)
        
        # 输出信息区域
        output_frame = ttk.LabelFrame(main_frame, text="输出信息", padding="10")
        output_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 分割线
        separator = ttk.Separator(output_frame, orient=tk.HORIZONTAL)
        separator.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 左下：账号1输出信息
        output1_frame = ttk.LabelFrame(output_frame, text="账号1输出信息", padding="10")
        output1_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.output_text1 = tk.Text(output1_frame, wrap=tk.WORD, height=15)
        self.output_text1.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar1 = ttk.Scrollbar(output1_frame, orient=tk.VERTICAL, command=self.output_text1.yview)
        scrollbar1.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.output_text1.configure(yscrollcommand=scrollbar1.set)
        
        # 右下：账号2输出信息
        output2_frame = ttk.LabelFrame(output_frame, text="账号2输出信息", padding="10")
        output2_frame.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.output_text2 = tk.Text(output2_frame, wrap=tk.WORD, height=15)
        self.output_text2.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar2 = ttk.Scrollbar(output2_frame, orient=tk.VERTICAL, command=self.output_text2.yview)
        scrollbar2.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.output_text2.configure(yscrollcommand=scrollbar2.set)
        
        # 配置网格权重
        output_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(1, weight=1)
        output_frame.rowconfigure(1, weight=1)
        
        # 绑定事件
        self.account_combo1.bind('<Return>', lambda e: self.execute_tasks())
        self.account_combo2.bind('<Return>', lambda e: self.execute_tasks())
    
    def execute_tasks(self):
        """执行任务"""
        # 验证输入
        if not self.account_var1.get():
            messagebox.showerror("错误", "请选择账号1")
            return
        
        if not self.account_var2.get():
            messagebox.showerror("错误", "请选择账号2")
            return
        
        # 显示执行开始信息
        self.output_text1.insert(tk.END, f"账号1开始执行任务...\n")
        self.output_text1.see(tk.END)
        self.output_text2.insert(tk.END, f"账号2开始执行任务...\n")
        self.output_text2.see(tk.END)
        
        # 启动多线程任务
        for i in range(2):  # 两个账号
            thread = threading.Thread(target=self.run_task, args=(i,))
            thread.start()
            self.running_threads.append(thread)
            
        # 更新UI
        self.execute_btn.config(state='disabled')
        
    def run_task(self, account_id):
        """运行单个任务"""
        # 模拟任务执行过程
        task_name = ["账号1", "账号2"][account_id]
        output_text = [self.output_text1, self.output_text2][account_id]
        
        output_text.insert(tk.END, f"{task_name}正在执行...\n")
        output_text.see(tk.END)
        
        # 模拟处理时间
        time.sleep(2)
        
        # 模拟任务结果
        result = "成功" if account_id % 2 == 0 else "失败"
        output_text.insert(tk.END, f"{task_name}执行完成，结果：{result}\n")
        output_text.see(tk.END)
        
        # 任务完成后更新UI
        if len(self.running_threads) == 0:
            self.execute_btn.config(state='normal')

def main():
    """主函数"""
    root = tk.Tk()
    app = YibanGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()