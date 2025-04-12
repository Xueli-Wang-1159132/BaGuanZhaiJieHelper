import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import calendar
from recurring_sun_generator import RecurringSunEventGenerator  # 假设你已保存前面类为 recurring_sun_generator.py


class CalendarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("太阳提醒日历生成器")

        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.grid(row=0, column=0, sticky="nsew")

        # 年份设置
        ttk.Label(frame, text="开始年份:").grid(row=0, column=0, sticky="e")
        self.start_year = tk.IntVar(value=2025)
        ttk.Entry(frame, textvariable=self.start_year, width=6).grid(row=0, column=1)

        ttk.Label(frame, text="结束年份:").grid(row=0, column=2, sticky="e")
        self.end_year = tk.IntVar(value=2030)
        ttk.Entry(frame, textvariable=self.end_year, width=6).grid(row=0, column=3)

        # 规则选择
        ttk.Label(frame, text="重复规则:").grid(row=1, column=0, sticky="e")
        self.rule_type = tk.StringVar()
        self.rule_combo = ttk.Combobox(frame, textvariable=self.rule_type, width=25, state="readonly")
        self.rule_combo['values'] = [
            "每月的第几天",
            "每季度（第一天或最后一天）",
            "某月的第几个星期几"
        ]
        self.rule_combo.current(0)
        self.rule_combo.grid(row=1, column=1, columnspan=3, sticky="w")

        # 规则参数输入
        self.param_frame = ttk.LabelFrame(frame, text="规则参数", padding=10)
        self.param_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky="ew")
        self.update_rule_inputs()

        self.rule_combo.bind("<<ComboboxSelected>>", lambda e: self.update_rule_inputs())

        # 保存按钮
        self.filename = tk.StringVar(value="sun_events.ics")
        ttk.Label(frame, text="保存为:").grid(row=4, column=0, sticky="e")
        ttk.Entry(frame, textvariable=self.filename, width=20).grid(row=4, column=1, columnspan=2, sticky="w")
        ttk.Button(frame, text="选择文件...", command=self.choose_file).grid(row=4, column=3)

        ttk.Button(frame, text="生成 .ics 日历", command=self.generate_calendar).grid(row=5, column=0, columnspan=4, pady=10)

    def update_rule_inputs(self):
        for widget in self.param_frame.winfo_children():
            widget.destroy()

        rule = self.rule_type.get()
        if rule == "每月的第几天":
            ttk.Label(self.param_frame, text="日 (1-31):").grid(row=0, column=0)
            self.day_var = tk.IntVar(value=1)
            ttk.Entry(self.param_frame, textvariable=self.day_var, width=5).grid(row=0, column=1)
        elif rule == "每季度（第一天或最后一天）":
            ttk.Label(self.param_frame, text="哪一天:").grid(row=0, column=0)
            self.quarter_var = tk.StringVar(value="first")
            ttk.Combobox(self.param_frame, textvariable=self.quarter_var, values=["first", "last"], width=10).grid(row=0, column=1)
        elif rule == "某月的第几个星期几":
            ttk.Label(self.param_frame, text="月份 (1-12):").grid(row=0, column=0)
            self.month_var = tk.IntVar(value=6)
            ttk.Entry(self.param_frame, textvariable=self.month_var, width=5).grid(row=0, column=1)

            ttk.Label(self.param_frame, text="星期 (0=一,6=日):").grid(row=0, column=2)
            self.weekday_var = tk.IntVar(value=6)
            ttk.Entry(self.param_frame, textvariable=self.weekday_var, width=5).grid(row=0, column=3)

            ttk.Label(self.param_frame, text="第几个:").grid(row=0, column=4)
            self.which_var = tk.StringVar(value="last")
            ttk.Combobox(self.param_frame, textvariable=self.which_var, values=["first", "last"], width=10).grid(row=0, column=5)

    def choose_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".ics")
        if file_path:
            self.filename.set(file_path)

    def generate_calendar(self):
        try:
            gen = RecurringSunEventGenerator(self.start_year.get(), self.end_year.get())

            rule = self.rule_type.get()
            if rule == "每月的第几天":
                gen.generate_by_monthly_day(day=self.day_var.get())
            elif rule == "每季度（第一天或最后一天）":
                gen.generate_by_quarter(which=self.quarter_var.get())
            elif rule == "某月的第几个星期几":
                gen.generate_by_weekday_rule(
                    month=self.month_var.get(),
                    weekday=self.weekday_var.get(),
                    which=self.which_var.get()
                )

            gen.save_to_ics(self.filename.get())
            messagebox.showinfo("完成", f".ics 文件已保存至:\n{self.filename.get()}")
        except Exception as e:
            messagebox.showerror("出错了", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = CalendarGUI(root)
    root.mainloop()
