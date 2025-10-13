# 将指定格式的文本文件合并保存为Markdown，以便提供给AI作为参考。
# 末伏之夜 出品
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Checkbutton, BooleanVar, Button, Frame, Label

# --- 配置区 ---

CONFIG_DIR = 'file_type_configs'

# 新增配置项：是否允许用户选择输出目录
# 如果设为 True，程序会弹窗让用户选择输出目录
# 如果设为 False，则按照原有逻辑自动选择输出目录
ALLOW_CHOOSE_OUTPUT_DIR = True  # 默认为True，允许用户选择输出目录

# 预设的可供选择的、包含其内容的文本文件后缀名
# 可以根据需要增删此列表
CANDIDATE_EXTENSIONS = [
    '.py', '.pyw', '.java', '.c', '.h', '.cpp', '.hpp', '.cs', '.go',
    '.js', '.ts', '.jsx', '.tsx', '.html', '.htm', '.css', '.scss', '.sass',
    '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.sh', '.bat', '.ps1', '.sql', '.r', '.swift', '.kt', '.kts',
    '.md', '.txt', '.rst', 'LICENSE', 'Dockerfile', '.vue', '.env', '.gitattributes',
    '.gitignore', '.j2', '.prisma'
]

# 文件后缀名到 Markdown 语言标识符的映射，用于语法高亮
LANGUAGE_MAP = {
    '.py': 'python',
    '.pyw': 'python',
    '.java': 'java',
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.jsx': 'jsx',
    '.tsx': 'tsx',
    '.html': 'html',
    '.htm': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.json': 'json',
    '.xml': 'xml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.ini': 'ini',
    '.cfg': 'ini',
    '.conf': 'ini',
    '.sh': 'shell',
    '.bat': 'batch',
    '.ps1': 'powershell',
    '.sql': 'sql',
    '.r': 'r',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.kts': 'kotlin',
    '.md': 'markdown',
    '.txt': 'text',
    '.rst': 'rst',
    'LICENSE': 'text',
    'Dockerfile': 'dockerfile',
    '.vue': 'html',
    '.env': 'ini',
    '.gitattributes': 'ini',
    '.gitignore': 'ini',
    '.j2': 'markdown',
    '.prisma': 'text'
}

# 在生成文件树时要忽略的目录和文件
IGNORED_ITEMS = {'.git', '__pycache__', '.vscode', 'node_modules', '.idea', '.DS_Store'}


# --- 功能函数 ---

def select_file_types():
    """
    创建一个窗口让用户选择要包含内容的文件类型。
    返回一个包含所选后缀名的列表，如果用户取消则返回 None。
    """
    selector_window = Toplevel()
    selector_window.title("请选择要包含内容的文件类型")

    # 保证窗口在最前
    selector_window.attributes('-topmost', True)

    vars = {}
    for ext in CANDIDATE_EXTENSIONS:
        vars[ext] = BooleanVar(value=True)  # 默认全选

    def toggle_all(select):
        for var in vars.values():
            var.set(select)

    # 创建复选框
    frame = Frame(selector_window, padx=10, pady=10)
    frame.pack(fill="both", expand=True)
    Label(frame, text="选择要读取并保存内容的文件类型:").grid(row=0, column=0, columnspan=4, sticky='w')

    # 将选项分多列展示
    num_columns = 4
    for i, ext in enumerate(CANDIDATE_EXTENSIONS):
        row = (i // num_columns) + 1
        col = i % num_columns
        cb = Checkbutton(frame, text=ext, variable=vars[ext])
        cb.grid(row=row, column=col, sticky='w', padx=5, pady=2)

    # --- 保存/读取预设配置UI部分 ---
    config_frame = Frame(selector_window, padx=10, pady=10)
    config_frame.pack(fill="x", expand=True)

    # 加载预设的下拉菜单
    Label(config_frame, text="加载预设:").pack(side="left", padx=(0, 5))

    preset_var = tk.StringVar(selector_window)
    presets_menu = tk.OptionMenu(config_frame, preset_var, "选择一个预设...")
    presets_menu.pack(side="left", fill="x", expand=True)

    # 保存预设的输入框和按钮
    Label(config_frame, text="另存为:").pack(side="left", padx=(10, 5))

    preset_name_entry = tk.Entry(config_frame)
    preset_name_entry.pack(side="left", fill="x", expand=True)

    save_btn = Button(config_frame, text="保存")
    save_btn.pack(side="left", padx=5)
    # --- 保存/读取预设配置UI部分结束 ---

    # 按钮区域
    btn_frame = Frame(selector_window, padx=10, pady=5)
    btn_frame.pack(fill="x")
    Button(btn_frame, text="全选", command=lambda: toggle_all(True)).pack(side="left", padx=5)
    Button(btn_frame, text="全不选", command=lambda: toggle_all(False)).pack(side="left", padx=5)

    selected_extensions = None

    # 保存预设辅助函数
    def get_presets():
        """扫描配置目录并返回预设名称列表"""
        try:
            # 仅列出目录中存在的 .json 文件名（不含后缀）
            return [os.path.splitext(f)[0] for f in os.listdir(CONFIG_DIR) if f.endswith('.json')]
        except FileNotFoundError:
            return []

    def refresh_presets_menu():
        """刷新下拉菜单中的预设列表"""
        presets = get_presets()
        menu = presets_menu["menu"]
        menu.delete(0, "end")
        if not presets:
            menu.add_command(label="无可用预设", state="disabled")
        else:
            for preset in presets:
                # 当菜单项被点击时，调用 load_preset 函数
                menu.add_command(label=preset, command=lambda p=preset: load_preset(p))
        preset_var.set("选择一个预设...")

    def load_preset(preset_name):
        """根据名称加载预设并更新复选框"""
        filepath = os.path.join(CONFIG_DIR, f"{preset_name}.json")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                selected_extensions = json.load(f)

            # 更新所有复选框的状态
            for ext, var in vars.items():
                if ext in selected_extensions:
                    var.set(True)
                else:
                    var.set(False)

            preset_name_entry.delete(0, tk.END)
            preset_name_entry.insert(0, preset_name)  # 将加载的预设名填入输入框，方便覆盖保存

        except Exception as e:
            messagebox.showerror("错误", f"加载预设 '{preset_name}' 失败: {e}")

    def save_preset():
        """保存当前勾选状态为一个新的预设文件"""
        preset_name = preset_name_entry.get().strip()
        if not preset_name:
            messagebox.showwarning("提示", "请输入预设名称后再保存。")
            return

        # 获取当前所有勾选的项
        current_selection = [ext for ext, var in vars.items() if var.get()]
        filepath = os.path.join(CONFIG_DIR, f"{preset_name}.json")

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(current_selection, f, indent=4)

            messagebox.showinfo("成功", f"预设 '{preset_name}' 已成功保存。")
            refresh_presets_menu()  # 保存后立即刷新下拉列表

        except Exception as e:
            messagebox.showerror("错误", f"保存预设失败: {e}")

    # 将 save_preset 函数绑定到保存按钮
    save_btn.config(command=save_preset)

    # 初始化时刷新一次预设菜单
    refresh_presets_menu()

    selected_extensions = None

    def on_ok():
        nonlocal selected_extensions
        selected_extensions = [ext for ext, var in vars.items() if var.get()]
        selector_window.destroy()

    Button(btn_frame, text="确定", command=on_ok, width=15).pack(side="right", padx=5)

    # 等待窗口关闭
    selector_window.transient()
    selector_window.wait_window()

    return selected_extensions


def generate_tree_structure(directory):
    """
    生成目录的树状结构字符串。
    """
    tree_lines = [f"📁 {os.path.basename(directory)}/"]

    def build_tree(current_path, prefix=""):
        try:
            items = sorted(os.listdir(current_path))
        except (PermissionError, OSError) as e:
            tree_lines.append(f"{prefix}└── [权限不足，无法访问: {os.path.basename(current_path)}]")
            return

        pointers = ['├── '] * (len(items) - 1) + ['└── ']

        for pointer, item in zip(pointers, items):
            if item in IGNORED_ITEMS:
                continue

            path = os.path.join(current_path, item)
            tree_lines.append(f"{prefix}{pointer}{item}")

            if os.path.isdir(path):
                extension = '│   ' if pointer == '├── ' else '    '
                try:
                    build_tree(path, prefix + extension)
                except (PermissionError, OSError) as e:
                    tree_lines.append(f"{prefix}{extension}└── [权限不足，无法访问: {item}]")

    build_tree(directory)
    return "\n".join(tree_lines)


def main_process():
    """
    主流程函数。
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)

    root = tk.Tk()
    root.withdraw()

    # 1. 让用户选择文件类型
    selected_types = select_file_types()
    if selected_types is None:
        messagebox.showinfo("提示", "操作已取消。")
        return

    # 2. 让用户选择文件夹
    folder_path = filedialog.askdirectory(title="请选择一个项目文件夹")
    if not folder_path:
        messagebox.showinfo("提示", "您没有选择任何文件夹。")
        return

    # 3. 准备输出文件
    folder_name = os.path.basename(folder_path)

    # 根据配置项决定输出路径的获取方式
    if ALLOW_CHOOSE_OUTPUT_DIR:
        # 允许用户选择输出目录
        output_dir = filedialog.askdirectory(
            title="请选择Markdown文件的输出目录",
            initialdir=os.path.dirname(folder_path)  # 默认打开项目文件夹的上级目录
        )
        if not output_dir:
            messagebox.showinfo("提示", "您没有选择输出目录，操作已取消。")
            return
        output_md_path = os.path.join(output_dir, f"{folder_name}.md")
    else:
        # 按照原有逻辑自动选择输出目录
        output_md_path = os.path.join(os.path.dirname(folder_path), f"{folder_name}.md")

    try:
        with open(output_md_path, 'w', encoding='utf-8') as md_file:
            # 写入主标题
            md_file.write(f"# 项目概览: {folder_name}\n\n")

            # 4. 写入文件结构树
            md_file.write("## 1. 项目文件结构\n\n")
            md_file.write("```\n")
            tree_structure = generate_tree_structure(folder_path)
            md_file.write(tree_structure)
            md_file.write("\n```\n\n")

            md_file.write("---\n\n")
            md_file.write("## 2. 文件内容详情\n\n")

            # 5. 遍历文件夹，写入选定文件内容
            for dirpath, _, filenames in os.walk(folder_path):
                # 忽略指定目录
                if any(part in IGNORED_ITEMS for part in dirpath.split(os.sep)):
                    continue

                # 尝试访问目录，如果权限不足则跳过
                try:
                    # 测试是否可访问该目录
                    os.listdir(dirpath)
                except (PermissionError, OSError) as e:
                    continue

                relative_path = os.path.relpath(dirpath, folder_path)
                depth = relative_path.count(os.sep) if relative_path != '.' else 0

                if relative_path != '.':
                    md_file.write(f"{'#' * (depth + 3)} 目录: `{relative_path.replace(os.sep, '/')}`\n\n")

                for filename in sorted(filenames):
                    if filename in IGNORED_ITEMS:
                        continue

                    _, extension = os.path.splitext(filename)

                    md_file.write(f"{'#' * (depth + 4)} `{filename}`\n\n")

                    if extension.lower() in selected_types:
                        file_path = os.path.join(dirpath, filename)
                        language = LANGUAGE_MAP.get(extension.lower(), 'text')
                        md_file.write(f"```{language}\n")
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                md_file.write(f.read())
                        except (PermissionError, OSError) as e:
                            md_file.write(f"# 错误: 无法读取文件内容. 原因: {e}")
                        except Exception as e:
                            md_file.write(f"# 错误: 读取文件时发生意外错误. 原因: {e}")
                        md_file.write("\n```\n\n")

        messagebox.showinfo("成功", f"Markdown 文件已成功生成！\n\n路径: {output_md_path}")

    except Exception as e:
        messagebox.showerror("错误", f"生成过程中发生错误：\n{e}")


if __name__ == "__main__":
    main_process()
