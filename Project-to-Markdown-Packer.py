# 将指定格式的文本文件合并保存为Markdown，以便提供给AI作为参考。
# 末伏之夜 出品
import os
import json
import fnmatch
import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, BooleanVar, Button, Frame, Label, Canvas, Scrollbar, LabelFrame, \
    Radiobutton, IntVar

# --- 配置区 ---

CONFIG_DIR = 'file_type_configs'

# 1. 是否遵循 .gitignore 规则
USE_GITIGNORE_CONFIG = True

# 2. 单个文件最大大小限制 (KB)
MAX_FILE_SIZE_KB = 500

# --- 后缀名分类结构 (UI显示用) ---
EXTENSION_CATEGORIES = {
    "文档": [
        '.md', '.txt', '.rst', 'LICENSE'
    ],
    "配置 & 开发运维": [
        '.sh', '.bat', '.ps1', 'Dockerfile', 'Makefile', '.gradle', '.properties', '.conf', '.cfg',
        '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.env', '.example', '.gitignore'
    ],
    "Python & Data": [
        '.py', '.pyw', '.ipynb',
    ],
    "网页开发": [
        '.html', '.htm', '.css', '.scss', '.sass', '.less',
        '.js', '.ts', '.jsx', '.tsx', '.vue', '.svelte'
    ],
    "后端 / 系统": [
        '.java', '.c', '.h', '.cpp', '.hpp', '.cs', '.go', '.rs', '.php', '.rb', '.lua', '.pl'
    ],
    "Godot引擎": [
        '.gd', '.tscn', '.tres', '.gdshader', 'project.godot', '.cs'
    ],
    "移动应用": [
        '.swift', '.kt', '.kts', '.dart'
    ],
    "数据库": [
        '.sql', '.prisma'
    ],
    "其他": [
        '.sol', '.v', '.sv', '.clj', '.ex', '.exs'
    ]
}

# --- 语言映射表 (用于Markdown高亮) ---
LANGUAGE_MAP = {
    # Python
    '.py': 'python', '.pyw': 'python', '.ipynb': 'json',
    # Java/Kotlin
    '.java': 'java', '.kt': 'kotlin', '.kts': 'kotlin', '.gradle': 'groovy', '.properties': 'ini',
    # C/C++
    '.c': 'c', '.h': 'c', '.cpp': 'cpp', '.hpp': 'cpp',
    # C#
    '.cs': 'csharp',
    # Web
    '.js': 'javascript', '.ts': 'typescript', '.jsx': 'jsx', '.tsx': 'tsx',
    '.html': 'html', '.htm': 'html', '.css': 'css', '.scss': 'scss', '.sass': 'sass', '.less': 'less',
    '.vue': 'html', '.svelte': 'html',
    # Godot
    '.gd': 'gdscript', '.tscn': 'ini', '.tres': 'ini', '.gdshader': 'glsl', 'project.godot': 'ini',
    # Go/Rust
    '.go': 'go', '.rs': 'rust',
    # PHP
    '.php': 'php',
    # Ruby/Lua/Perl
    '.rb': 'ruby', '.lua': 'lua', '.pl': 'perl',
    # Mobile
    '.swift': 'swift', '.dart': 'dart',
    # Config/Data
    '.json': 'json', '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
    '.toml': 'toml', '.ini': 'ini', '.cfg': 'ini', '.conf': 'ini', '.env': 'ini', '.example': 'ini',
    # Shell
    '.sh': 'shell', '.bat': 'batch', '.ps1': 'powershell',
    '.gitattributes': 'ini', '.gitignore': 'ini', 'Dockerfile': 'dockerfile', 'Makefile': 'makefile',
    # SQL
    '.sql': 'sql', '.prisma': 'text',
    # Docs
    '.md': 'markdown', '.txt': 'text', '.rst': 'rst', 'LICENSE': 'text',
    # Others
    '.sol': 'solidity', '.v': 'verilog', '.sv': 'systemverilog',
    '.clj': 'clojure', '.ex': 'elixir', '.exs': 'elixir'
}

IGNORED_ITEMS_ALWAYS = {'.git', '__pycache__', '.vscode', 'node_modules', '.idea', '.DS_Store', 'dist', 'build', 'venv',
                        '.venv', 'target', '.godot', '.import'}


# --- 辅助类与函数 ---

class GitIgnoreMatcher:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.patterns = []
        if USE_GITIGNORE_CONFIG:
            self.load_gitignore()

    def load_gitignore(self):
        gitignore_path = os.path.join(self.root_dir, '.gitignore')
        if not os.path.exists(gitignore_path):
            return
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    self.patterns.append(line)
        except Exception:
            pass

    def is_ignored(self, file_path):
        if not self.patterns:
            return False
        rel_path = os.path.relpath(file_path, self.root_dir)
        rel_path_unix = rel_path.replace(os.sep, '/')
        filename = os.path.basename(file_path)
        for pattern in self.patterns:
            if pattern.endswith('/'):
                norm_pattern = pattern.rstrip('/')
                if rel_path_unix.startswith(pattern) or f"/{norm_pattern}/" in f"/{rel_path_unix}":
                    return True
            if fnmatch.fnmatch(filename, pattern):
                return True
            if fnmatch.fnmatch(rel_path_unix, pattern):
                return True
        return False


def center_window(window, width=None, height=None):
    window.update_idletasks()
    w = width or window.winfo_width()
    h = height or window.winfo_height()
    ws = window.winfo_screenwidth()
    hs = window.winfo_screenheight()
    x = (ws / 2) - (w / 2)
    y = (hs / 2) - (h / 2)
    window.geometry(f'+{int(x)}+{int(y)}')


def select_options():
    """配置窗口：选择文件类型及输出路径"""
    selector_window = Toplevel()
    selector_window.title("导出配置")
    selector_window.geometry("800x600")
    center_window(selector_window, 800, 600)
    selector_window.attributes('-topmost', True)

    # 变量存储
    ext_vars = {}  # { '.py': BooleanVar, ... }

    # 初始化所有变量
    for cat, exts in EXTENSION_CATEGORIES.items():
        for ext in exts:
            ext_vars[ext] = BooleanVar(value=True)

    # --- 布局结构 ---
    # 1. 顶部：预设管理
    top_frame = Frame(selector_window, padx=10, pady=10, bg="#e0e0e0")
    top_frame.pack(side="top", fill="x")

    # 2. 底部：输出选项 + 开始按钮
    bottom_frame = Frame(selector_window, padx=15, pady=15, bg="#f0f0f0", bd=1, relief="sunken")
    bottom_frame.pack(side="bottom", fill="x")

    # 3. 中间：滚动区域（存放复选框）
    container_frame = Frame(selector_window)
    container_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)

    canvas = Canvas(container_frame, highlightthickness=0)
    scrollbar = Scrollbar(container_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    # 鼠标滚轮绑定
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", on_mousewheel)
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # --- 1. 顶部预设功能 ---
    Label(top_frame, text="预设配置:", bg="#e0e0e0").pack(side="left")
    preset_var = tk.StringVar(selector_window)
    presets_menu = tk.OptionMenu(top_frame, preset_var, "选择预设...")
    presets_menu.pack(side="left", padx=5)

    preset_name_entry = tk.Entry(top_frame, width=15)
    preset_name_entry.pack(side="left", padx=5)

    def get_presets():
        if not os.path.exists(CONFIG_DIR): return []
        return [os.path.splitext(f)[0] for f in os.listdir(CONFIG_DIR) if f.endswith('.json')]

    def load_preset(name):
        try:
            with open(os.path.join(CONFIG_DIR, f"{name}.json"), 'r') as f:
                saved = json.load(f)
            # 先清空
            for v in ext_vars.values(): v.set(False)
            # 再选中
            for ext in saved:
                if ext in ext_vars: ext_vars[ext].set(True)
            preset_name_entry.delete(0, tk.END)
            preset_name_entry.insert(0, name)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def save_preset():
        name = preset_name_entry.get().strip()
        if not name: return messagebox.showwarning("警告", "请输入预设名称")
        selected = [ext for ext, v in ext_vars.items() if v.get()]
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(os.path.join(CONFIG_DIR, f"{name}.json"), 'w') as f:
            json.dump(selected, f)
        messagebox.showinfo("成功", "预设已保存")
        refresh_menu()

    save_btn = Button(top_frame, text="保存当前配置", command=save_preset)
    save_btn.pack(side="left")

    def refresh_menu():
        menu = presets_menu["menu"]
        menu.delete(0, "end")
        presets = get_presets()
        if not presets:
            menu.add_command(label="无预设", state="disabled")
        else:
            for p in presets:
                menu.add_command(label=p, command=lambda x=p: load_preset(x))
        preset_var.set("加载预设...")

    refresh_menu()

    # --- 3. 中间分类复选框生成 ---

    def toggle_category(category_name, state):
        exts = EXTENSION_CATEGORIES[category_name]
        for ext in exts:
            ext_vars[ext].set(state)

    for category, extensions in EXTENSION_CATEGORIES.items():
        # 创建一个带标题的框 (LabelFrame)
        cat_frame = LabelFrame(scrollable_frame, text=f" {category} ", font=("Arial", 10, "bold"), padx=10, pady=5)
        cat_frame.pack(fill="x", expand=True, padx=5, pady=5)

        # 顶部工具栏（全选/全不选）
        tool_frame = Frame(cat_frame)
        tool_frame.pack(anchor="w", fill="x", pady=(0, 5))

        Button(tool_frame, text="全选", font=("Arial", 8), width=6,
               command=lambda c=category: toggle_category(c, True)).pack(side="left", padx=2)
        Button(tool_frame, text="清空", font=("Arial", 8), width=6,
               command=lambda c=category: toggle_category(c, False)).pack(side="left", padx=2)

        # 网格布局复选框
        grid_frame = Frame(cat_frame)
        grid_frame.pack(fill="x")

        cols = 5
        for i, ext in enumerate(extensions):
            r, c = divmod(i, cols)
            cb = tk.Checkbutton(grid_frame, text=ext, variable=ext_vars[ext])
            cb.grid(row=r, column=c, sticky="w", padx=5)

    # --- 2. 底部输出选项 ---

    # 输出模式变量: 0 = 原目录, 1 = 自定义目录
    output_mode_var = IntVar(value=0)

    opt_label = Label(bottom_frame, text="输出位置:", font=("Arial", 10, "bold"), bg="#f0f0f0")
    opt_label.pack(side="left", padx=(0, 10))

    rb1 = Radiobutton(bottom_frame, text="项目根目录 (默认)", variable=output_mode_var, value=0, bg="#f0f0f0")
    rb1.pack(side="left", padx=5)

    rb2 = Radiobutton(bottom_frame, text="自定义目录...", variable=output_mode_var, value=1, bg="#f0f0f0")
    rb2.pack(side="left", padx=5)

    # 全局全选/全不选
    def global_toggle(state):
        for v in ext_vars.values():
            v.set(state)

    global_btn_frame = Frame(bottom_frame, bg="#f0f0f0")
    global_btn_frame.pack(side="left", padx=30)
    Button(global_btn_frame, text="所有全选", command=lambda: global_toggle(True)).pack(side="left")
    Button(global_btn_frame, text="所有清空", command=lambda: global_toggle(False)).pack(side="left", padx=5)

    # 确定按钮
    result = None

    def on_confirm():
        nonlocal result
        selected = [ext for ext, var in ext_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("提示", "请至少选择一种文件类型")
            return

        result = {
            "extensions": selected,
            "output_custom": (output_mode_var.get() == 1)
        }
        canvas.unbind_all("<MouseWheel>")
        selector_window.destroy()

    Button(bottom_frame, text="开始生成 Markdown", command=on_confirm,
           bg="#007bff", fg="white", font=("Arial", 11, "bold"), padx=20).pack(side="right")

    selector_window.wait_window()
    return result


def generate_tree_structure(directory):
    tree_lines = [f"📁 {os.path.basename(directory)}/"]

    def build_tree(current_path, prefix=""):
        try:
            items = sorted(os.listdir(current_path))
        except OSError:
            tree_lines.append(f"{prefix}└── [无法访问]")
            return
        filtered_items = [item for item in items if item not in IGNORED_ITEMS_ALWAYS]
        count = len(filtered_items)
        for i, item in enumerate(filtered_items):
            path = os.path.join(current_path, item)
            is_last = (i == count - 1)
            pointer = '└── ' if is_last else '├── '
            tree_lines.append(f"{prefix}{pointer}{item}")
            if os.path.isdir(path):
                extension = '    ' if is_last else '│   '
                build_tree(path, prefix + extension)

    build_tree(directory)
    return "\n".join(tree_lines)


def main_process():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    root = tk.Tk()
    root.withdraw()

    # 1. 弹出配置窗口
    config = select_options()
    if config is None:
        return

    selected_types = config['extensions']
    use_custom_output = config['output_custom']

    # 2. 选择项目文件夹
    folder_path = filedialog.askdirectory(title="请选择要转换的项目根目录")
    if not folder_path:
        return

    folder_name = os.path.basename(folder_path)

    # 3. 确定输出路径
    if use_custom_output:
        output_dir = filedialog.askdirectory(title="选择 Markdown 保存位置")
        if not output_dir: return
        output_md_path = os.path.join(output_dir, f"{folder_name}_project.md")
    else:
        # 输出到项目根目录的上一级，或者项目根目录内部（这里保持原逻辑：输出到项目同级目录避免污染）
        # 如果你想输出到项目内部，改为 os.path.join(folder_path, ...)
        output_md_path = os.path.join(os.path.dirname(folder_path), f"{folder_name}.md")

    git_matcher = GitIgnoreMatcher(folder_path)

    try:
        with open(output_md_path, 'w', encoding='utf-8') as md_file:
            md_file.write(f"# 项目概览: {folder_name}\n\n")
            if USE_GITIGNORE_CONFIG:
                md_file.write("> 💡 注：已启用 .gitignore 过滤，忽略文件的具体内容未包含在内。\n\n")

            md_file.write("## 1. 项目文件结构\n\n```text\n")
            md_file.write(generate_tree_structure(folder_path))
            md_file.write("\n```\n\n---\n\n")

            md_file.write("## 2. 文件内容详情\n\n")
            file_count = 0
            skipped_count = 0

            for dirpath, dirnames, filenames in os.walk(folder_path):
                # 过滤文件夹
                dirnames[:] = [d for d in dirnames if d not in IGNORED_ITEMS_ALWAYS]
                # GitIgnore 过滤文件夹层级
                if USE_GITIGNORE_CONFIG and git_matcher.is_ignored(dirpath):
                    dirnames[:] = []  # 如果文件夹被忽略，不进入子目录
                    continue

                for filename in sorted(filenames):
                    if filename in IGNORED_ITEMS_ALWAYS: continue
                    file_path = os.path.join(dirpath, filename)

                    if USE_GITIGNORE_CONFIG and git_matcher.is_ignored(file_path):
                        continue

                    _, ext = os.path.splitext(filename)
                    ext_lower = ext.lower()

                    if ext_lower in selected_types or filename in selected_types:  # 支持像 Makefile 这种无后缀匹配
                        try:
                            file_size_kb = os.path.getsize(file_path) / 1024
                            if file_size_kb > MAX_FILE_SIZE_KB:
                                md_file.write(f"> ⚠️ 文件 `{filename}` 过大 ({file_size_kb:.1f}KB)，已跳过内容。\n\n")
                                continue
                        except OSError:
                            continue

                        display_rel_path = os.path.relpath(file_path, folder_path).replace(os.sep, '/')
                        md_file.write(f"#### 📄 `{display_rel_path}`\n\n")

                        language = LANGUAGE_MAP.get(ext_lower, 'text')
                        # 特殊文件名处理
                        if filename == 'Dockerfile': language = 'dockerfile'
                        if filename == 'Makefile': language = 'makefile'

                        md_file.write(f"```{language}\n")

                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if '\0' in content:
                                    md_file.write(f" (检测到二进制内容，已跳过)\n")
                                else:
                                    md_file.write(content)
                        except Exception as e:
                            md_file.write(f"无法读取文件: {e}")

                        md_file.write("\n```\n\n")
                        file_count += 1
                    else:
                        skipped_count += 1

        summary = f"Markdown 文件已生成！\n\n路径: {output_md_path}\n\n- 包含文件数: {file_count}\n- 忽略/跳过数: {skipped_count}"
        messagebox.showinfo("完成", summary)

    except Exception as e:
        messagebox.showerror("严重错误", f"发生未捕获异常:\n{e}")


if __name__ == "__main__":
    main_process()

if __name__ == "__main__":
    main_process()
