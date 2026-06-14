# CCNU Course Planner

本项目是本地化选课辅助工具，支持读取学校发布的 Excel 选课手册、搜索课程、加入已选课程、检测时间冲突、生成可视化课表并导出 Excel。

## 运行环境

依赖：

```bash
pip install -r requirements.txt
```

`main.py` 启动时会先检查 `requirements.txt` 中的依赖。如果当前 Python 环境缺少依赖，程序会自动执行：

```bash
python -m pip install -r requirements.txt
```

运行程序：

```bash
python main.py
```

## 输入文件

程序默认从 `class_table/` 目录中寻找 `.xlsx` 文件，并优先加载文件名包含“选课手册”的 Excel 文件。

默认文件：

```text
class_table/附件2：2026-2027学年第一学期选课手册.xlsx
```

程序只读加载原始 Excel，不会移动、覆盖或修改该文件。界面中可以通过“选择文件”切换同类选课手册。

## 功能

- 使用 `ttkbootstrap` 主题优化界面；如果库不可用，程序会回退到普通 `ttk`。
- 自动遍历工作簿所有工作表。
- 自动识别包含“课程名称”“上课时间”的表头。
- 解析中文上课时间和单双周规则。
- 支持按空格分隔的多关键词联合搜索。
- 支持加入、移除、清空已选课程。
- 支持显示并屏蔽与已选课程冲突的搜索结果。
- 实时显示周一到周日、第 1 到第 12 节的可视化课表。
- 搜索框带 300 毫秒防抖，搜索结果默认最多显示前 300 条。
- 课程加载后会预先生成搜索文本和占用时间槽，提升搜索和冲突判断速度。
- 点击搜索结果、已选课程或课表格子可查看完整课程详情。
- 导出 `exports/selected_timetable.xlsx`，包含“已选课程”“解析结果”“可视化课表”三个工作表。

## 测试

```bash
python -m pytest
```

测试覆盖时间解析、冲突检测和搜索逻辑。

## 主要文件

- `main.py`：项目入口。
- `src/app.py`：Tkinter 图形界面。
- `src/excel_loader.py`：Excel 读取和字段兼容映射。
- `src/time_parser.py`：中文课程时间解析。
- `src/conflict_checker.py`：课程冲突检测。
- `src/search_engine.py`：课程关键词搜索和屏蔽冲突。
- `src/timetable.py`：可视化课表数据生成。
- `src/exporter.py`：导出已选课程和课表 Excel。
