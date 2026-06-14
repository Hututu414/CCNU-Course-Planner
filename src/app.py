from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

try:
    import ttkbootstrap as tb
except ImportError:  # pragma: no cover - exercised only when optional UI dependency is absent.
    tb = None

from .conflict_checker import (
    build_selected_course_map,
    build_selected_slots,
    conflicts_with_any,
    conflicts_with_slots,
)
from .excel_loader import load_courses_from_excel
from .exporter import export_selected_courses
from .models import Course
from .search_engine import search_courses
from .timetable import (
    WEEKDAY_LABELS,
    build_timetable_cell_entries,
    format_meeting,
    selected_conflict_summary,
    stable_course_colors,
)
from .utils import DEFAULT_CLASS_TABLE_DIR, course_key, find_default_excel_path, shorten_text


MAX_SEARCH_RESULTS = 300
SEARCH_DEBOUNCE_MS = 300


class Tooltip:
    def __init__(self, widget: tk.Widget, text_provider) -> None:
        self.widget = widget
        self.text_provider = text_provider
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, _event=None) -> None:
        text = self.text_provider()
        if not text or self.tip_window is not None:
            return
        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip_window,
            text=text,
            justify=tk.LEFT,
            background="#fffff4",
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=6,
            wraplength=420,
        )
        label.pack()

    def hide(self, _event=None) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class CoursePlannerApp:
    def __init__(self, root: tk.Tk, default_path: Path | None = None) -> None:
        self.root = root
        self.root.title("CCNU Course Planner")
        self.root.geometry("1440x900")
        self.root.minsize(1100, 720)

        self.excel_path = tk.StringVar(value=str(default_path or ""))
        self.query = tk.StringVar()
        self.hide_conflicts = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="未加载课程")

        self.courses: list[Course] = []
        self.filtered_courses: list[Course] = []
        self.selected_courses: list[Course] = []
        self.selected_slots: set[tuple[int, int, int]] = set()
        self.selected_by_key: dict[tuple[str, int, str, str, str], Course] = {}
        self.result_items: dict[str, Course] = {}
        self.selected_items: dict[str, Course] = {}
        self.timetable_cells: dict[tuple[int, int], tk.Text] = {}
        self.timetable_entries: dict[tuple[int, int], list[dict]] = {}

        self.search_after_id: str | None = None
        self.results_truncated = False
        self.current_result_count = 0
        self.conflict_summaries: list[str] = []

        self.base_font = tkfont.nametofont("TkDefaultFont")
        self.small_font = self.base_font.copy()
        self.small_font.configure(size=max(8, self.base_font.cget("size") - 1))
        self.bold_font = self.base_font.copy()
        self.bold_font.configure(weight="bold")

        self._configure_styles()
        self._build_ui()
        self.query.trace_add("write", self._schedule_search)

        if default_path:
            self.load_courses()
        else:
            self._update_status()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.configure("Treeview", rowheight=28)
        style.configure("Treeview.Heading", font=self.bold_font)
        style.configure("Status.TLabel", padding=(10, 5))
        style.configure("Toolbar.TFrame", padding=(10, 8))

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_toolbar()

        body = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

        left = ttk.PanedWindow(body, orient=tk.VERTICAL)
        right = ttk.PanedWindow(body, orient=tk.VERTICAL)
        body.add(left, weight=3)
        body.add(right, weight=2)

        self._build_results(left)
        self._build_details(left)
        self._build_selected(right)
        self._build_timetable(right)

        status_bar = ttk.Label(self.root, textvariable=self.status, style="Status.TLabel", anchor=tk.W)
        status_bar.grid(row=2, column=0, sticky="ew")

    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)
        toolbar.columnconfigure(5, weight=1)

        ttk.Label(toolbar, text="文件").grid(row=0, column=0, sticky="w")
        ttk.Entry(toolbar, textvariable=self.excel_path).grid(row=0, column=1, sticky="ew", padx=(6, 8))
        ttk.Button(toolbar, text="选择文件", command=self.choose_file).grid(row=0, column=2, padx=2)
        ttk.Button(toolbar, text="重新加载", command=self.load_courses).grid(row=0, column=3, padx=2)

        ttk.Label(toolbar, text="搜索").grid(row=0, column=4, sticky="w", padx=(14, 4))
        search_entry = ttk.Entry(toolbar, textvariable=self.query)
        search_entry.grid(row=0, column=5, sticky="ew", padx=(0, 6))
        search_entry.bind("<Return>", lambda _event: self.refresh_results())
        ttk.Button(toolbar, text="搜索", command=self.refresh_results).grid(row=0, column=6, padx=2)
        ttk.Button(toolbar, text="显示全部", command=self.show_all).grid(row=0, column=7, padx=2)
        ttk.Checkbutton(
            toolbar,
            text="屏蔽冲突课程",
            variable=self.hide_conflicts,
            command=self.refresh_results,
        ).grid(row=0, column=8, padx=(8, 0))

    def _build_results(self, pane: ttk.PanedWindow) -> None:
        frame = ttk.LabelFrame(pane, text="搜索结果", padding=8)
        pane.add(frame, weight=4)

        self.result_columns = ("name", "teacher", "credit", "time", "campus", "classroom", "exam", "status", "warning")
        self.result_tree = ttk.Treeview(frame, columns=self.result_columns, show="headings", height=18, selectmode="extended")
        headings = {
            "name": "课程名称",
            "teacher": "教师",
            "credit": "学分",
            "time": "上课时间",
            "campus": "校区",
            "classroom": "教室",
            "exam": "考核",
            "status": "状态",
            "warning": "解析警告",
        }
        widths = {
            "name": 180,
            "teacher": 130,
            "credit": 54,
            "time": 270,
            "campus": 70,
            "classroom": 90,
            "exam": 70,
            "status": 76,
            "warning": 110,
        }
        for column in self.result_columns:
            self.result_tree.heading(column, text=headings[column])
            self.result_tree.column(column, width=widths[column], minwidth=48, stretch=column in {"name", "time"})
        self.result_tree.tag_configure("conflict", background="#ffe8e8", foreground="#9f1239")
        self.result_tree.tag_configure("warning", background="#fff7ed")
        self.result_tree.tag_configure("selected", background="#edf7ff")
        self.result_tree.bind("<<TreeviewSelect>>", self._show_result_detail)

        y_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        x_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        button_row = ttk.Frame(frame)
        button_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(button_row, text="加入已选", command=self.add_selected).pack(side=tk.LEFT)

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    def _build_details(self, pane: ttk.PanedWindow) -> None:
        frame = ttk.LabelFrame(pane, text="课程详情", padding=8)
        pane.add(frame, weight=1)

        self.detail_text = tk.Text(
            frame,
            height=8,
            wrap=tk.WORD,
            font=self.base_font,
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=6,
        )
        detail_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scroll.set, state=tk.DISABLED)
        self.detail_text.grid(row=0, column=0, sticky="nsew")
        detail_scroll.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self._set_detail_text("点击搜索结果或已选课程后，这里会显示完整课程信息。")

    def _build_selected(self, pane: ttk.PanedWindow) -> None:
        frame = ttk.LabelFrame(pane, text="已选课程", padding=8)
        pane.add(frame, weight=1)

        self.selected_columns = ("name", "teacher", "credit", "time", "status")
        self.selected_tree = ttk.Treeview(frame, columns=self.selected_columns, show="headings", height=7, selectmode="extended")
        headings = {"name": "课程名称", "teacher": "教师", "credit": "学分", "time": "上课时间", "status": "状态"}
        widths = {"name": 150, "teacher": 105, "credit": 54, "time": 210, "status": 70}
        for column in self.selected_columns:
            self.selected_tree.heading(column, text=headings[column])
            self.selected_tree.column(column, width=widths[column], minwidth=46, stretch=column in {"name", "time"})
        self.selected_tree.tag_configure("conflict", background="#ffe8e8", foreground="#9f1239")
        self.selected_tree.bind("<<TreeviewSelect>>", self._show_selected_detail)

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.selected_tree.yview)
        self.selected_tree.configure(yscrollcommand=scroll.set)
        self.selected_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        controls = ttk.Frame(frame)
        controls.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(controls, text="移除已选", command=self.remove_selected).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(controls, text="清空已选", command=self.clear_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="导出课表", command=self.export_timetable).pack(side=tk.LEFT, padx=4)
        self.selected_summary = ttk.Label(controls, text="")
        self.selected_summary.pack(side=tk.LEFT, padx=(12, 0))

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    def _build_timetable(self, pane: ttk.PanedWindow) -> None:
        frame = ttk.LabelFrame(pane, text="可视化课表", padding=8)
        pane.add(frame, weight=3)

        ttk.Label(frame, text="节次", anchor=tk.CENTER, font=self.bold_font).grid(row=0, column=0, sticky="nsew")
        for weekday_index, label in enumerate(WEEKDAY_LABELS, start=1):
            ttk.Label(frame, text=label, anchor=tk.CENTER, font=self.bold_font).grid(row=0, column=weekday_index, sticky="nsew", padx=1)

        for section in range(1, 13):
            ttk.Label(frame, text=f"第{section}节", anchor=tk.CENTER, width=7).grid(
                row=section,
                column=0,
                sticky="nsew",
                padx=1,
                pady=1,
            )
            for weekday in range(1, 8):
                cell = tk.Text(
                    frame,
                    height=4,
                    width=15,
                    wrap=tk.WORD,
                    font=self.small_font,
                    relief=tk.SOLID,
                    borderwidth=1,
                    padx=4,
                    pady=3,
                    cursor="arrow",
                    takefocus=0,
                )
                cell.grid(row=section, column=weekday, sticky="nsew", padx=1, pady=1)
                cell.configure(state=tk.DISABLED)
                cell.tooltip_text = ""
                cell.bind("<Button-1>", lambda _event, key=(section, weekday): self._show_timetable_detail(key))
                Tooltip(cell, lambda widget=cell: getattr(widget, "tooltip_text", ""))
                self.timetable_cells[(section, weekday)] = cell

        for column in range(8):
            frame.columnconfigure(column, weight=1 if column else 0)
        for row in range(13):
            frame.rowconfigure(row, weight=1 if row else 0)

    def choose_file(self) -> None:
        initial_dir = DEFAULT_CLASS_TABLE_DIR if DEFAULT_CLASS_TABLE_DIR.exists() else Path.cwd()
        path = filedialog.askopenfilename(
            title="选择选课手册 Excel",
            initialdir=str(initial_dir),
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if path:
            self.excel_path.set(path)
            self.load_courses()

    def load_courses(self) -> None:
        path = self.excel_path.get().strip()
        if not path:
            messagebox.showwarning("未选择文件", "请先选择选课手册 Excel 文件。")
            return
        try:
            self.status.set("正在加载课程，请稍候...")
            self.root.update_idletasks()
            self.courses = load_courses_from_excel(path)
        except Exception as exc:
            messagebox.showerror("加载失败", f"无法加载选课手册：\n{exc}")
            self.status.set("加载失败")
            return
        self.selected_courses.clear()
        self._rebuild_selected_indexes()
        self.refresh_selected(redraw_timetable=True, refresh_results_after=False)
        self.refresh_results()

    def show_all(self) -> None:
        self.query.set("")
        self.refresh_results()

    def _schedule_search(self, *_args) -> None:
        if self.search_after_id is not None:
            self.root.after_cancel(self.search_after_id)
        self.search_after_id = self.root.after(SEARCH_DEBOUNCE_MS, self.refresh_results)

    def refresh_results(self) -> None:
        if self.search_after_id is not None:
            self.root.after_cancel(self.search_after_id)
            self.search_after_id = None

        matches = search_courses(
            self.courses,
            self.query.get(),
            self.hide_conflicts.get(),
            self.selected_courses,
            selected_slots=self.selected_slots,
            limit=MAX_SEARCH_RESULTS + 1,
        )
        self.results_truncated = len(matches) > MAX_SEARCH_RESULTS
        self.filtered_courses = matches[:MAX_SEARCH_RESULTS]
        self.current_result_count = len(self.filtered_courses)
        self._replace_result_rows()
        self._update_status()

    def _replace_result_rows(self) -> None:
        self._prepare_tree_for_bulk_update(self.result_tree)
        self.result_tree.delete(*self.result_tree.get_children())
        self.result_items.clear()

        for index, course in enumerate(self.filtered_courses):
            item_id = f"result-{index}"
            is_selected = course_key(course) in self.selected_by_key
            is_conflict = conflicts_with_slots(course, self.selected_slots, selected_by_key=self.selected_by_key)
            tags = []
            if is_conflict:
                tags.append("conflict")
            if course.parse_warning:
                tags.append("warning")
            if is_selected:
                tags.append("selected")
            self.result_items[item_id] = course
            self.result_tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=(
                    course.name,
                    course.teacher,
                    "" if course.credit is None else course.credit,
                    shorten_text(course.raw_time, 80),
                    course.campus,
                    course.classroom,
                    course.exam_type,
                    "已选" if is_selected else ("冲突" if is_conflict else ""),
                    course.parse_warning,
                ),
                tags=tuple(tags),
            )
        self._finish_tree_bulk_update(self.result_tree, self.result_columns)

    def add_selected(self) -> None:
        item_ids = self.result_tree.selection()
        if not item_ids:
            messagebox.showinfo("未选择课程", "请先在搜索结果中选择课程。")
            return

        added = 0
        existing_keys = set(self.selected_by_key)
        working_slots = set(self.selected_slots)
        for item_id in item_ids:
            course = self.result_items.get(item_id)
            if course is None or course_key(course) in existing_keys:
                continue
            if conflicts_with_slots(course, working_slots):
                ok = messagebox.askyesno("课程冲突", f"{course.name} 与已选课程冲突，是否仍然加入？")
                if not ok:
                    continue
            self.selected_courses.append(course)
            existing_keys.add(course_key(course))
            working_slots.update(course.occupied_slots)
            added += 1
        if added:
            self.refresh_selected(redraw_timetable=True, refresh_results_after=True)

    def remove_selected(self) -> None:
        item_ids = self.selected_tree.selection()
        if not item_ids:
            messagebox.showinfo("未选择课程", "请先在已选课程中选择要移除的课程。")
            return
        remove_keys = {
            course_key(course)
            for item_id in item_ids
            if (course := self.selected_items.get(item_id)) is not None
        }
        self.selected_courses = [course for course in self.selected_courses if course_key(course) not in remove_keys]
        self.refresh_selected(redraw_timetable=True, refresh_results_after=True)

    def clear_selected(self) -> None:
        if not self.selected_courses:
            return
        if messagebox.askyesno("清空已选", "确定清空所有已选课程吗？"):
            self.selected_courses.clear()
            self.refresh_selected(redraw_timetable=True, refresh_results_after=True)

    def refresh_selected(self, redraw_timetable: bool, refresh_results_after: bool) -> None:
        self._rebuild_selected_indexes()
        self.conflict_summaries = selected_conflict_summary(self.selected_courses)

        self._prepare_tree_for_bulk_update(self.selected_tree)
        self.selected_tree.delete(*self.selected_tree.get_children())
        self.selected_items.clear()

        for index, course in enumerate(self.selected_courses):
            item_id = f"selected-{index}"
            is_conflict = conflicts_with_any(course, self.selected_courses)
            tags = ["conflict"] if is_conflict else [self._course_row_tag(course)]
            self.selected_items[item_id] = course
            self.selected_tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=(
                    course.name,
                    course.teacher,
                    "" if course.credit is None else course.credit,
                    shorten_text(course.raw_time, 70),
                    "冲突" if is_conflict else "",
                ),
                tags=tuple(tags),
            )
        self._finish_tree_bulk_update(self.selected_tree, self.selected_columns)

        total_credit = self._total_credit()
        conflict_text = f"，冲突 {len(self.conflict_summaries)} 组" if self.conflict_summaries else "，无冲突"
        self.selected_summary.configure(text=f"已选 {len(self.selected_courses)} 门，总学分 {total_credit:g}{conflict_text}")

        if redraw_timetable:
            self._refresh_timetable()
        if refresh_results_after:
            self.refresh_results()
        else:
            self._update_status()

    def _refresh_timetable(self) -> None:
        grid = build_timetable_cell_entries(self.selected_courses)
        self.timetable_entries.clear()
        for section in range(1, 13):
            for weekday in range(1, 8):
                entries = grid[section - 1][weekday - 1]
                key = (section, weekday)
                self.timetable_entries[key] = entries
                cell = self.timetable_cells[key]
                self._render_timetable_cell(cell, entries)

    def _render_timetable_cell(self, cell: tk.Text, entries: list[dict]) -> None:
        if any(entry["conflict"] for entry in entries):
            background = "#fff0f0"
        elif len(entries) == 1:
            background = entries[0]["background"]
        elif entries:
            background = "#fff8e6"
        else:
            background = "white"

        cell.configure(state=tk.NORMAL, background=background)
        cell.delete("1.0", tk.END)
        for index, entry in enumerate(entries[:2]):
            if index:
                cell.insert(tk.END, "\n")
            tag_name = f"course_{index}"
            cell.tag_configure(tag_name, font=self.bold_font, foreground=entry["foreground"])
            if entry["conflict"]:
                cell.tag_configure(f"{tag_name}_conflict", font=self.bold_font, foreground="#b00020")
                cell.insert(tk.END, entry["title"], (tag_name, f"{tag_name}_conflict"))
            else:
                cell.insert(tk.END, entry["title"], (tag_name,))
            if entry["details"]:
                cell.insert(tk.END, f"\n{entry['details']}")
        if len(entries) > 2:
            cell.insert(tk.END, f"\n另有 {len(entries) - 2} 门")
        cell.tooltip_text = "\n\n".join(entry["full_text"] for entry in entries)
        cell.configure(state=tk.DISABLED)

    def export_timetable(self) -> None:
        if not self.selected_courses:
            messagebox.showinfo("无已选课程", "请先加入至少一门课程。")
            return
        try:
            export_path = export_selected_courses(self.selected_courses, str(Path.cwd() / "exports"))
        except Exception as exc:
            messagebox.showerror("导出失败", f"无法导出课表：\n{exc}")
            return
        messagebox.showinfo("导出完成", f"已导出：\n{export_path}")

    def _show_result_detail(self, _event=None) -> None:
        item_ids = self.result_tree.selection()
        if item_ids and (course := self.result_items.get(item_ids[0])) is not None:
            self._show_course_detail(course)

    def _show_selected_detail(self, _event=None) -> None:
        item_ids = self.selected_tree.selection()
        if item_ids and (course := self.selected_items.get(item_ids[0])) is not None:
            self._show_course_detail(course)

    def _show_timetable_detail(self, key: tuple[int, int]) -> None:
        entries = self.timetable_entries.get(key, [])
        if not entries:
            return
        if len(entries) == 1:
            self._show_course_detail(entries[0]["course"])
            return
        text = [f"{WEEKDAY_LABELS[key[1] - 1]} 第{key[0]}节包含 {len(entries)} 门课程："]
        for entry in entries:
            course = entry["course"]
            marker = "冲突" if entry["conflict"] else "课程"
            text.append(f"\n[{marker}] {course.name}\n{entry['full_text']}")
        self._set_detail_text("\n".join(text))

    def _show_course_detail(self, course: Course) -> None:
        lines = [
            f"课程名称：{course.name}",
            f"课程编号：{course.course_id}",
            f"教师：{course.teacher}",
            f"学分：{'' if course.credit is None else course.credit}",
            f"校区：{course.campus}",
            f"教室：{course.classroom}",
            f"考核方式：{course.exam_type}",
            f"课程类别：{course.category}",
            f"来源：{course.source_sheet} 第 {course.source_row} 行",
            f"原始上课时间：{course.raw_time}",
        ]
        if course.parse_warning:
            lines.append(f"解析警告：{course.parse_warning}")
        lines.append("")
        lines.append("解析结果：")
        if course.meetings:
            for meeting in course.meetings:
                weekday = WEEKDAY_LABELS[meeting.weekday - 1] if 1 <= meeting.weekday <= 7 else f"周{meeting.weekday}"
                parity = {"all": "全部", "odd": "单周", "even": "双周"}.get(meeting.parity, meeting.parity)
                lines.append(
                    f"- {weekday} 第{meeting.start_section}-{meeting.end_section}节，{format_meeting(meeting)}，{parity}"
                )
        else:
            lines.append("- 暂无可用解析结果")
        self._set_detail_text("\n".join(lines))

    def _set_detail_text(self, text: str) -> None:
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state=tk.DISABLED)

    def _rebuild_selected_indexes(self) -> None:
        self.selected_slots = build_selected_slots(self.selected_courses)
        self.selected_by_key = build_selected_course_map(self.selected_courses)

    def _course_row_tag(self, course: Course) -> str:
        tag = f"course_{abs(hash(course_key(course)))}"
        background, foreground = stable_course_colors(course)
        self.selected_tree.tag_configure(tag, background=background, foreground=foreground)
        return tag

    def _prepare_tree_for_bulk_update(self, tree: ttk.Treeview) -> None:
        try:
            tree.configure(displaycolumns=())
        except tk.TclError:
            pass

    def _finish_tree_bulk_update(self, tree: ttk.Treeview, columns: tuple[str, ...]) -> None:
        try:
            tree.configure(displaycolumns=columns)
        except tk.TclError:
            pass

    def _total_credit(self) -> float:
        return sum(course.credit or 0 for course in self.selected_courses)

    def _update_status(self) -> None:
        parts = [
            f"总课程 {len(self.courses)}",
            f"当前显示 {self.current_result_count}",
            f"已选 {len(self.selected_courses)}",
            f"总学分 {self._total_credit():g}",
        ]
        parts.append(f"冲突 {len(self.conflict_summaries)} 组" if self.conflict_summaries else "无冲突")
        if self.results_truncated:
            parts.append("结果过多，仅显示前 300 条，请继续缩小关键词")
        if tb is None:
            parts.append("ttkbootstrap 不可用，已回退普通 ttk")
        self.status.set(" | ".join(parts))


def run_app() -> None:
    root = tb.Window(themename="flatly") if tb is not None else tk.Tk()
    CoursePlannerApp(root, find_default_excel_path())
    root.mainloop()
