"""
DocX 优雅阅读器 - DocX2TXT GUI
本地 docx 文件读取与格式化导出工具
技术栈：PyQt6 + Python 内置 zipfile/xml
"""

import sys, os, zipfile, re, xml.etree.ElementTree as ET
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QTextEdit, QFileDialog, QMessageBox,
    QLabel, QSizePolicy, QProgressDialog
)
from PyQt6.QtCore import Qt, QMimeData, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor

# ──────────────────────────────────────────────────────────────
# 解析引擎
# ──────────────────────────────────────────────────────────────
NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

SERVICE_KW = [
    '十指弹琴', '过水服务', '胸滑', '舌尖漫游', '舌尖毒龙',
    '共浴', '浴室挑逗', '水中萧', '花式吹箫', '69互动',
    '激情爱爱', '各类制服',
]

def parse_docx(filepath: str) -> list[str]:
    """返回 docx 中的原始段落列表（<w:br/> 转为换行）"""
    paragraphs = []
    try:
        with zipfile.ZipFile(filepath) as z:
            with z.open('word/document.xml') as f:
                root = ET.parse(f).getroot()

        def get_text(para):
            parts = []
            for elem in para.iter():
                if elem.tag == f'{{{NS}}}t' and elem.text:
                    parts.append(elem.text)
                elif elem.tag == f'{{{NS}}}br':
                    parts.append('\n')
            return ''.join(parts)

        for para in root.iter(f'{{{NS}}}p'):
            text = get_text(para)
            for line in text.split('\n'):
                line = line.replace('\xa0', ' ').replace('\t', ' ').strip()
                if line:
                    paragraphs.append(line)
    except Exception as e:
        raise RuntimeError(f"解析失败：{e}")
    return paragraphs


def format_docx_content(paragraphs: list[str]) -> str:
    """将段落列表格式化为好看的纯文本"""
    DIV = "─" * 42
    lines = []

    def section(title, body=None):
        lines.extend(['', DIV, f"　{title}", DIV])
        if body:
            for b in body:
                lines.append(f"　◆ {b}")

    price_collected = []
    SERVICE_RE = re.compile(
        '(' + '|'.join(re.escape(k) for k in SERVICE_KW) + r')((（[^）]*）)?)'
    )

    def split_services(text):
        text = re.sub(r'^服务[：:\s\xa0]*', '', text).replace('\xa0', ' ')
        items, last_end = [], 0
        for m in SERVICE_RE.finditer(text):
            if m.start() > last_end:
                pass
            items.append(m.group(1) + (m.group(2) or ''))
            last_end = m.end()
        if last_end < len(text):
            tail = text[last_end:].strip()
            if tail and items:
                items[-1] += tail
        return items

    def fmt_price(raw):
        raw = raw.replace('\xa0', ' ').strip()
        raw = re.sub(r'^价格\s*', '', raw)
        m = re.match(r'^([PpP]+)\s*(\d[\d分钟次小时]*)', raw)
        if m:
            prefix, val = m.group(1), m.group(2)
            tag = '双人套餐' if prefix.upper() == 'PP' else '单次体验'
            return f"　{tag}　　{prefix}{val}"
        mm = re.match(r'^包时\s*(\d[\d分钟次小时]*)', raw)
        if mm:
            return f"　包时套餐　包时{mm.group(1)}"
        return f"　{raw}"

    for p in paragraphs:
        p = p.replace('\xa0', ' ').strip()
        if not p:
            continue
        if re.search(r'[Pp]\d{3,}|包时', p):
            price_collected.append(p); continue
        if '惠州市' in p:
            addr = re.sub(r'^地址\s*', '', p).strip()
            lines.extend(['', DIV, '　地址', DIV, f"　　{addr}"])
        elif '🈲' in p:
            bans = re.findall(r'🈲([^🈲\s]{1,4})', p)
            lines.extend(['', DIV, '　备注', DIV,
                         f"　　禁止：{'　'.join(bans)}"])
        elif '自我评价' in p:
            body = re.sub(r'^自我评价\s*', '', p).strip()
            lines.extend(['', DIV, '　自我评价', DIV, f"　　{body}"])
        elif re.search(r'\d{2}年|身高\d|体重\d|胸围', p):
            parts = [x for x in re.split(r'[，,\s、]+', p) if x]
            section('基本信息', parts)
        elif any(kw in p for kw in SERVICE_KW):
            section('服务项目', split_services(p))
        else:
            lines.append(p)

    if price_collected:
        lines.extend(['', DIV, '　服务价格', DIV])
        for pv in price_collected:
            lines.append(fmt_price(pv))

    lines.extend(['', DIV])
    return '\n'.join(lines)


def docx_to_markdown(paragraphs: list[str]) -> str:
    """将段落列表转为 Markdown 格式"""
    lines = ["# 文档内容\n"]

    def section(title, body=None):
        lines.append(f"\n## {title}\n")
        if body:
            for b in body:
                lines.append(f"- {b}")

    price_collected = []
    SERVICE_RE = re.compile(
        '(' + '|'.join(re.escape(k) for k in SERVICE_KW) + r')((（[^）]*）)?)'
    )

    def split_services(text):
        text = re.sub(r'^服务[：:\s\xa0]*', '', text).replace('\xa0', ' ')
        items, last_end = [], 0
        for m in SERVICE_RE.finditer(text):
            items.append(m.group(1) + (m.group(2) or ''))
            last_end = m.end()
        if last_end < len(text):
            tail = text[last_end:].strip()
            if tail and items:
                items[-1] += tail
        return items

    for p in paragraphs:
        p = p.replace('\xa0', ' ').strip()
        if not p:
            continue
        if re.search(r'[Pp]\d{3,}|包时', p):
            price_collected.append(p); continue
        if '惠州市' in p:
            lines.append(f"\n## 地址\n\n{re.sub(r'^地址\s*', '', p)}\n")
        elif '🈲' in p:
            bans = re.findall(r'🈲([^🈲\s]{1,4})', p)
            lines.append(f"\n## 备注\n\n**禁止：** {' / '.join(bans)}\n")
        elif '自我评价' in p:
            lines.append(f"\n## 自我评价\n\n{re.sub(r'^自我评价\s*', '', p)}\n")
        elif re.search(r'\d{2}年|身高\d|体重\d|胸围', p):
            parts = [x for x in re.split(r'[，,\s、]+', p) if x]
            section('基本信息', parts)
        elif any(kw in p for kw in SERVICE_KW):
            section('服务项目', split_services(p))

    if price_collected:
        lines.append("\n## 服务价格\n")
        for pv in price_collected:
            pv = pv.replace('\xa0', ' ').strip()
            pv = re.sub(r'^价格\s*', '', pv)
            m = re.match(r'^([PpP]+)\s*(\d[\d分钟次小时]*)', pv)
            if m:
                tag = '双人套餐' if m.group(1).upper() == 'PP' else '单次体验'
                lines.append(f"- **{tag}**：{m.group(1)}{m.group(2)}\n")
            elif pv.startswith('包时'):
                mm = re.match(r'包时\s*(\d[\d分钟次小时]*)', pv)
                if mm:
                    lines.append(f"- **包时套餐**：{mm.group(1)}\n")

    return ''.join(lines)


# ──────────────────────────────────────────────────────────────
# 主窗口
# ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.files = []          # [(filepath, filename, paragraphs, formatted_text)]
        self.current = -1
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("DocX 优雅阅读器")
        self.setGeometry(300, 100, 1100, 750)
        self.setAcceptDrops(True)

        # ── 中心部件 ──
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ── 左侧：文件列表 ──
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        title_label = QLabel("📄 已加载文件")
        title_label.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        left_layout.addWidget(title_label)

        self.file_list = QListWidget()
        self.file_list.setFont(QFont("Microsoft YaHei UI", 10))
        self.file_list.itemClicked.connect(self.on_file_clicked)
        left_layout.addWidget(self.file_list)

        # 按钮栏
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("＋ 添加文件")
        self.btn_add.clicked.connect(self.add_files)
        self.btn_remove = QPushButton("－ 移除")
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self.clear_all)
        for btn in (self.btn_add, self.btn_remove, self.btn_clear):
            btn.setFont(QFont("Microsoft YaHei UI", 9))
            btn.setMinimumHeight(32)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_clear)
        left_layout.addLayout(btn_layout)

        # 左侧宽度
        left_widget.setMaximumWidth(280)
        left_widget.setMinimumWidth(200)
        main_layout.addWidget(left_widget)

        # ── 右侧：预览区 ──
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        preview_title = QLabel("📋 内容预览")
        preview_title.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        right_layout.addWidget(preview_title)

        self.preview = QTextEdit()
        self.preview.setFont(QFont("Microsoft YaHei UI", 10))
        self.preview.setReadOnly(True)
        self.preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                padding: 12px;
                selection-background-color: #264f78;
            }
        """)
        right_layout.addWidget(self.preview)

        # 导出按钮栏
        export_layout = QHBoxLayout()
        self.btn_txt = QPushButton("导出 .txt")
        self.btn_txt.clicked.connect(self.export_txt)
        self.btn_md = QPushButton("导出 .md")
        self.btn_md.clicked.connect(self.export_md)
        for btn in (self.btn_txt, self.btn_md):
            btn.setFont(QFont("Microsoft YaHei UI", 9))
            btn.setMinimumHeight(36)
        self.btn_txt.setStyleSheet("background-color: #0078d4; color: white; border-radius: 4px;")
        self.btn_md.setStyleSheet("background-color: #333; color: white; border-radius: 4px;")
        export_layout.addWidget(self.btn_txt)
        export_layout.addWidget(self.btn_md)
        export_layout.addStretch()
        right_layout.addLayout(export_layout)

        main_layout.addWidget(right_widget, 1)

        # ── 状态栏 ──
        self.statusBar().showMessage("提示：拖拽 .docx 文件到窗口即可添加")

    # ── 文件添加 ──
    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择 DocX 文件", "",
            "Word 文档 (*.docx);;所有文件 (*)"
        )
        if paths:
            self.load_files(paths)

    def load_files(self, paths):
        progress = QProgressDialog("正在解析...", "取消", 0, len(paths), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        added = 0
        for i, fp in enumerate(paths):
            progress.setValue(i)
            if progress.wasCanceled():
                break
            fname = os.path.basename(fp)
            if any(f[1] == fname for f in self.files):
                continue
            try:
                paras = parse_docx(fp)
                formatted = format_docx_content(paras)
                self.files.append((fp, fname, paras, formatted))
                added += 1
            except Exception as e:
                QMessageBox.warning(self, "解析错误", f"文件：{fname}\n{e}")
        progress.setValue(len(paths))
        self.refresh_list(added)

    def refresh_list(self, added=0):
        self.file_list.clear()
        for _, fname, _, _ in self.files:
            self.file_list.addItem(fname)
        if self.files and added > 0:
            self.file_list.setCurrentRow(len(self.files) - added)
            self.on_file_clicked()
        elif self.files:
            self.file_list.setCurrentRow(self.current if 0 <= self.current < len(self.files) else 0)
            self.on_file_clicked()
        self.statusBar().showMessage(
            f"已加载 {len(self.files)} 个文件" if self.files else "提示：拖拽 .docx 文件到窗口即可添加"
        )

    def on_file_clicked(self):
        idx = self.file_list.currentRow()
        self.current = idx
        if 0 <= idx < len(self.files):
            _, _, _, formatted = self.files[idx]
            self.show_preview(formatted)

    def show_preview(self, text):
        self.preview.setPlainText(text)
        # 设置等宽字体（让内容对齐好看）
        cursor = self.preview.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

    # ── 拖放 ──
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls()]
        docx_paths = [p for p in paths if p.lower().endswith('.docx')]
        if docx_paths:
            self.load_files(docx_paths)
        else:
            QMessageBox.information(self, "提示", "请拖放 .docx 文件")

    # ── 移除 / 清空 ──
    def remove_selected(self):
        idx = self.file_list.currentRow()
        if 0 <= idx < len(self.files):
            self.files.pop(idx)
            self.refresh_list()

    def clear_all(self):
        self.files.clear()
        self.current = -1
        self.file_list.clear()
        self.preview.clear()
        self.statusBar().showMessage("已清空")

    # ── 导出 ──
    def do_export(self, ext: str, filter_str: str, conv):
        if not self.files:
            QMessageBox.information(self, "提示", "请先添加文件")
            return
        # 如果当前有选中文件，只导出那个；否则批量
        if 0 <= self.current < len(self.files):
            fp, fname = self.files[self.current][0], self.files[self.current][1]
            default_name = fname.rsplit('.', 1)[0] + ext
            out_path, _ = QFileDialog.getSaveFileName(
                self, "导出", default_name, filter_str)
            if not out_path:
                return
            _, _, paras, _ = self.files[self.current]
            content = conv(paras)
            with open(out_path, 'w', encoding='utf-8-sig') as f:
                f.write(content)
            QMessageBox.information(self, "完成", f"已导出：\n{out_path}")
        else:
            out_dir = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
            if not out_dir:
                return
            for fp, fname, paras, _ in self.files:
                out_name = Path(fp).stem + ext
                out_fp = os.path.join(out_dir, out_name)
                with open(out_fp, 'w', encoding='utf-8-sig') as f:
                    f.write(conv(paras))
            QMessageBox.information(self, "完成", f"已批量导出到：\n{out_dir}")

    def export_txt(self):
        self.do_export(".txt", "文本文件 (*.txt)", format_docx_content)

    def export_md(self):
        self.do_export(".md", "Markdown 文件 (*.md)", docx_to_markdown)


# ──────────────────────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
