"""
自动化评教工具主程序

该模块实现了一个基于Tkinter的图形界面应用程序，
用于管理和展示自动化评教工具的用户界面。
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import time
import random
import threading
import queue
import os
from datetime import datetime


def read_file_as_variables(file_path):
    """
    读取文本文件并返回行列表

    :param file_path: 文件路径
    :return: 包含文件各行的列表（已去除换行符）
    :raises FileNotFoundError: 文件不存在时抛出
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.read().splitlines()
    return lines


class AutoEvaluationApp:
    """
    自动化评教工具主应用类

    负责创建和管理图形界面，处理用户交互，
    管理应用状态和消息队列。
    """

    def __init__(self, root):
        """
        初始化应用程序

        :param root: Tkinter根窗口对象
        """
        self.root = root
        self.root.title("自动化评教工具")
        self.root.geometry("900x750")
        self.root.resizable(True, True)

        # 将窗口居中显示
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # 配置ttk主题样式
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TProgressbar", thickness=25)

        # 文件路径配置
        self.pjrwh_file_path = tk.StringVar(value="list.txt")
        self.file_path = tk.StringVar(value="user.txt")
        self.teacher_file_path = tk.StringVar(value="teacher.txt")
        self.teacher_mode_enabled = tk.BooleanVar(value=False)

        # 任务控制变量
        self.running = False
        self.paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()

        # 进度跟踪
        self.total_tasks = 0
        self.completed_tasks = 0

        # 消息队列
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()

        # 构建界面
        self.create_widgets()

        # 显示用户协议
        self.show_agreement()

    def create_widgets(self):
        """创建主界面所有组件"""
        # 主容器框架
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 应用标题
        title_label = ttk.Label(self.main_frame, text="自动化评教工具", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 15))

        # 文件配置区域
        file_frame = ttk.LabelFrame(self.main_frame, text="文件配置", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))

        # 评教任务编号文件输入
        ttk.Label(file_frame, text="评教任务编号文件:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.pjrwh_file_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=lambda: self.browse_file(self.pjrwh_file_path)).grid(row=0, column=2, padx=5, pady=5)

        # 学号文件输入
        ttk.Label(file_frame, text="学号文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=lambda: self.browse_file(self.file_path)).grid(row=1, column=2, padx=5, pady=5)

        # 教师名单文件输入及开关
        ttk.Label(file_frame, text="教师名单文件（自己人模式）:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.teacher_file_path, width=50).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="浏览", command=lambda: self.browse_file(self.teacher_file_path)).grid(row=2, column=2, padx=5, pady=5)
        ttk.Checkbutton(file_frame, text="启用", variable=self.teacher_mode_enabled,
                       command=self.on_teacher_mode_changed).grid(row=2, column=3, padx=5, pady=5)

        # 权重配置区域
        weight_frame = ttk.LabelFrame(self.main_frame, text="评价权重配置（权重越高选择几率越大）", padding=10)
        weight_frame.pack(fill=tk.X, pady=(0, 10))

        # 优秀权重滑块
        ttk.Label(weight_frame, text="优秀权重:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.excellent_weight = tk.IntVar(value=6)
        ttk.Scale(weight_frame, from_=0, to=10, variable=self.excellent_weight, orient=tk.HORIZONTAL,
                 length=200).grid(row=0, column=1, padx=5, pady=5)
        self.excellent_weight_label = ttk.Label(weight_frame, text="6")
        self.excellent_weight_label.grid(row=0, column=2, padx=5, pady=5)
        self.excellent_weight.trace_add("write", lambda *args: self.excellent_weight_label.config(text=str(self.excellent_weight.get())))

        # 良好权重滑块
        ttk.Label(weight_frame, text="良好权重:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.good_weight = tk.IntVar(value=4)
        ttk.Scale(weight_frame, from_=0, to=10, variable=self.good_weight, orient=tk.HORIZONTAL,
                 length=200).grid(row=1, column=1, padx=5, pady=5)
        self.good_weight_label = ttk.Label(weight_frame, text="4")
        self.good_weight_label.grid(row=1, column=2, padx=5, pady=5)
        self.good_weight.trace_add("write", lambda *args: self.good_weight_label.config(text=str(self.good_weight.get())))

        # 中等权重滑块
        ttk.Label(weight_frame, text="中等权重:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.fair_weight = tk.IntVar(value=1)
        ttk.Scale(weight_frame, from_=0, to=10, variable=self.fair_weight, orient=tk.HORIZONTAL,
                 length=200).grid(row=2, column=1, padx=5, pady=5)
        self.fair_weight_label = ttk.Label(weight_frame, text="1")
        self.fair_weight_label.grid(row=2, column=2, padx=5, pady=5)
        self.fair_weight.trace_add("write", lambda *args: self.fair_weight_label.config(text=str(self.fair_weight.get())))

        # 权重配置应用按钮
        ttk.Button(weight_frame, text="应用权重配置", command=self.apply_weight_config).grid(row=0, column=3, rowspan=3, padx=20)

        # 状态显示区域
        status_frame = ttk.LabelFrame(self.main_frame, text="当前状态", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # 状态信息容器
        left_frame = ttk.Frame(status_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 状态变量初始化
        self.current_user_var = tk.StringVar(value="当前用户: 等待开始")
        self.current_course_var = tk.StringVar(value="当前课程: 等待开始")
        self.current_teacher_var = tk.StringVar(value="当前教师: 等待开始")
        self.current_choice_var = tk.StringVar(value="评价结果: 等待开始")

        # 状态标签
        ttk.Label(left_frame, textvariable=self.current_user_var, font=("宋体", 10)).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(left_frame, textvariable=self.current_course_var, font=("宋体", 10)).grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(left_frame, textvariable=self.current_teacher_var, font=("宋体", 10)).grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Label(left_frame, textvariable=self.current_choice_var, font=("宋体", 10)).grid(row=3, column=0, sticky=tk.W, pady=2)

        # 操作按钮区域
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        # 开始评教按钮
        self.run_button = tk.Button(button_frame, text="开始评教", command=self.start_evaluation,
                                   bg="#4CAF50", fg="white", font=("Arial", 12), height=1)
        self.run_button.pack(side=tk.LEFT, padx=(0, 10))

        # 暂停评教按钮
        self.pause_button = tk.Button(button_frame, text="暂停评教", command=self.toggle_pause,
                                    bg="#FFC107", fg="black", font=("Arial", 12), height=1, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=(0, 10))

        # 终止评教按钮
        self.stop_button = tk.Button(button_frame, text="终止评教", command=self.stop_evaluation,
                                   bg="#F44336", fg="white", font=("Arial", 12), height=1, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))

        # 清空日志按钮
        self.clear_log_button = tk.Button(button_frame, text="清空日志", command=self.clear_log,
                                        bg="#9E9E9E", fg="white", font=("Arial", 12), height=1)
        self.clear_log_button.pack(side=tk.RIGHT, padx=(10, 0))

        # 日志显示区域
        log_frame = ttk.LabelFrame(self.main_frame, text="运行日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, font=("宋体", 12))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_agreement(self):
        """显示用户协议对话框"""
        # 创建半透明遮罩层
        self.overlay = tk.Frame(self.root, bg="#222222")
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # 协议内容容器
        self.agreement_frame = tk.Frame(self.overlay, bg="white", padx=20, pady=20)
        self.agreement_frame.place(relx=0.5, rely=0.5, anchor="center", width=600, height=450)

        # 协议文本内容
        agreement_text = """
用户协议

感谢使用自动化评教工具。在使用本工具前，请仔细阅读以下条款：

1. 本工具仅供学习和研究使用，不得用于任何非法或违反学校规定的活动。
2. 使用本工具可能违反学校的相关规定，使用者需自行承担可能的后果。
3. 开发者不对因使用本工具而导致的任何损失或后果承担责任。
4. 本工具可能会收集和使用您的个人信息，请确保您了解并同意这些信息的使用方式。
5. 未经允许，不得将本工具用于商业目的或进行二次分发。

通过点击"同意"按钮，您表示您已阅读并同意上述条款。如果您不同意这些条款，请点击"拒绝"。

本协议自您点击"同意"按钮之日起生效。
        """

        # 协议文本显示组件
        text_widget = scrolledtext.ScrolledText(self.agreement_frame, wrap=tk.WORD, font=("宋体", 10),
                                              bg="white", bd=0)
        text_widget.insert(tk.END, agreement_text)
        text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        text_widget.config(state=tk.DISABLED)

        # 倒计时显示标签
        self.countdown_var = tk.StringVar(value="30秒后可同意")
        countdown_label = tk.Label(self.agreement_frame, textvariable=self.countdown_var, font=("Arial", 12), bg="white")
        countdown_label.pack(pady=(0, 10))

        # 按钮容器
        button_frame = tk.Frame(self.agreement_frame, bg="white")
        button_frame.pack(fill=tk.X)

        # 拒绝按钮
        self.reject_button = tk.Button(button_frame, text="拒绝", command=self.reject_agreement,
                                     bg="#F44336", fg="white", font=("Arial", 14), width=15, height=2)
        self.reject_button.pack(side=tk.RIGHT, padx=(10, 0))

        # 同意按钮
        self.accept_button = tk.Button(button_frame, text="同意", command=self.accept_agreement,
                                     bg="#4CAF50", fg="white", font=("Arial", 14), width=15, height=2, state=tk.DISABLED)
        self.accept_button.pack(side=tk.RIGHT, padx=(0, 10))

        # 启动倒计时
        self.remaining_time = 3
        self.update_countdown()

    def update_countdown(self):
        """更新协议对话框倒计时"""
        if self.remaining_time > 0:
            self.countdown_var.set(f"{self.remaining_time}秒后可同意")
            self.remaining_time -= 1
            self.root.after(1000, self.update_countdown)
        else:
            self.countdown_var.set("已阅读并同意")
            self.accept_button.config(state=tk.NORMAL)

    def accept_agreement(self):
        """处理用户同意协议"""
        self.overlay.destroy()

    def reject_agreement(self):
        """处理用户拒绝协议"""
        self.root.destroy()

    def browse_file(self, var):
        """
        打开文件选择对话框

        :param var: StringVar对象，用于存储选择的文件路径
        """
        filename = filedialog.askopenfilename()
        if filename:
            var.set(filename)

    def log(self, message):
        """
        向日志区域写入消息

        :param message: 日志内容
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        """清空日志显示区域"""
        self.log_text.delete(1.0, tk.END)

    def on_teacher_mode_changed(self):
        """处理自己人模式开关状态变化"""
        if self.teacher_mode_enabled.get():
            self.log("🔘 已启用自己人模式")
        else:
            self.log("⚪ 已禁用自己人模式")

    def apply_weight_config(self):
        """处理权重配置应用"""
        excellent = self.excellent_weight.get()
        good = self.good_weight.get()
        fair = self.fair_weight.get()
        self.log(f"⚙️  权重配置：优秀={excellent}, 良好={good}, 中等={fair}")
        self.log("ℹ️  权重计算功能已禁用，此配置仅供界面演示")

    def process_log_queue(self):
        """处理日志队列消息"""
        while not self.log_queue.empty():
            try:
                message = self.log_queue.get_nowait()
                self.log(message)
            except queue.Empty:
                pass
        self.root.after(100, self.process_log_queue)

    def process_progress_queue(self):
        """处理进度队列消息"""
        while not self.progress_queue.empty():
            try:
                message_type, message = self.progress_queue.get_nowait()
                if message_type == "current_user":
                    self.current_user_var.set(message)
                elif message_type == "current_course":
                    self.current_course_var.set(message)
                elif message_type == "current_teacher":
                    self.current_teacher_var.set(message)
                elif message_type == "current_choice":
                    self.current_choice_var.set(message)
                elif message_type == "progress_update":
                    self.completed_tasks += message
                    self.update_progress()
            except queue.Empty:
                pass
        self.root.after(100, self.process_progress_queue)

    def start_evaluation(self):
        """开始评教任务"""
        if self.running:
            return

        # 应用当前权重配置
        self.apply_weight_config()

        # 初始化任务状态
        self.running = True
        self.paused = False
        self.stop_event.clear()
        self.pause_event.set()

        # 重置进度计数器
        self.completed_tasks = 0
        self.total_tasks = 0

        # 更新按钮状态
        self.run_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL, text="暂停评教")
        self.stop_button.config(state=tk.NORMAL)

        # 清理并初始化显示
        self.clear_log()
        self.current_user_var.set("当前用户: 准备中")
        self.current_course_var.set("当前课程: 准备中")
        self.current_teacher_var.set("当前教师: 准备中")
        self.current_choice_var.set("评价结果: 准备中")

        self.status_var.set("正在运行...")

        # 显示演示模式提示
        self.log("⚠️  此功能当前为演示模式，核心评教功能已禁用")
        self.log("📝 界面保留完整视觉样式和交互行为")
        self.log("⏱️  10秒后自动恢复就绪状态...")

        # 模拟任务执行并自动结束
        def simulate_complete():
            time.sleep(10)
            self.root.after(0, self.stop_evaluation)

        threading.Thread(target=simulate_complete, daemon=True).start()

    def toggle_pause(self):
        """切换任务暂停状态"""
        if self.paused:
            self.paused = False
            self.pause_event.set()
            self.pause_button.config(text="暂停评教")
            self.status_var.set("正在运行...")
            self.log("▶️  已继续（演示模式）")
        else:
            self.paused = True
            self.pause_event.clear()
            self.pause_button.config(text="继续评教")
            self.status_var.set("已暂停")
            self.log("⏸️  已暂停（演示模式）")

    def stop_evaluation(self):
        """停止评教任务"""
        if not self.running:
            return

        self.running = False
        self.paused = False
        self.stop_event.set()
        self.pause_event.set()

        # 恢复按钮状态
        self.run_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)

        self.status_var.set("就绪")
        self.log("🛑  已停止（演示模式）")
        self.log("✅  所有界面元素和交互行为保持完整")

    def update_progress(self):
        """更新任务进度显示"""
        pass


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoEvaluationApp(root)

    # 启动消息队列处理
    app.process_log_queue()
    app.process_progress_queue()

    root.mainloop()
