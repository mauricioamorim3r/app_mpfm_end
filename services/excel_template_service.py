from __future__ import annotations

import shutil
from copy import copy
from pathlib import Path


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
MONTHLY_WORKBOOK_TEMPLATE = TEMPLATES_DIR / "MPFM_MAR_template.xlsx"
SEP_EXPORT_TEMPLATE = TEMPLATES_DIR / "SEP_Dados_template.xlsx"
PRODUCTION_EXPORT_TEMPLATE = TEMPLATES_DIR / "dados_producao.xlsx"
EXCEL_FORMATTING_REFERENCE = TEMPLATES_DIR / "Excel_formatting_reference.xlsx"


def _as_path(value) -> Path:
    return value if isinstance(value, Path) else Path(value)


def ensure_workbook_from_template(workbook_path: Path, template_path: Path) -> None:
    workbook_path = _as_path(workbook_path)
    template_path = _as_path(template_path)
    if template_path.exists() and not workbook_path.exists():
        workbook_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template_path, workbook_path)


def copy_cell_style(src, dst) -> None:
    dst.font = copy(src.font)
    dst.fill = copy(src.fill)
    dst.border = copy(src.border)
    dst.alignment = copy(src.alignment)
    dst.number_format = src.number_format
    dst.protection = copy(src.protection)


def center_cell_content(cell) -> None:
    alignment = copy(cell.alignment)
    alignment.horizontal = "center"
    alignment.vertical = "center"
    cell.alignment = alignment


def center_filled_cells(ws, start_row: int = 1, start_col: int = 1) -> None:
    for row in ws.iter_rows(min_row=start_row, min_col=start_col):
        for cell in row:
            if cell.value is None or cell.value == "":
                continue
            center_cell_content(cell)


def copy_sheet_layout(src_ws, dst_ws) -> None:
    dst_ws.sheet_view.showGridLines = src_ws.sheet_view.showGridLines
    dst_ws.freeze_panes = src_ws.freeze_panes
    if src_ws.auto_filter and src_ws.auto_filter.ref:
        dst_ws.auto_filter.ref = src_ws.auto_filter.ref
    dst_ws.sheet_format.defaultColWidth = src_ws.sheet_format.defaultColWidth
    dst_ws.sheet_format.defaultRowHeight = src_ws.sheet_format.defaultRowHeight
    dst_ws.sheet_format.zeroHeight = src_ws.sheet_format.zeroHeight
    dst_ws.sheet_properties = copy(src_ws.sheet_properties)
    dst_ws.page_margins = copy(src_ws.page_margins)
    dst_ws.page_setup = copy(src_ws.page_setup)
    dst_ws.print_options = copy(src_ws.print_options)

    for merged in list(src_ws.merged_cells.ranges):
        dst_ws.merge_cells(str(merged))

    for col_letter, dim in src_ws.column_dimensions.items():
        dst_dim = dst_ws.column_dimensions[col_letter]
        dst_dim.width = dim.width
        dst_dim.hidden = dim.hidden
        dst_dim.bestFit = dim.bestFit
        dst_dim.outlineLevel = dim.outlineLevel

    for row_idx, dim in src_ws.row_dimensions.items():
        dst_dim = dst_ws.row_dimensions[row_idx]
        dst_dim.height = dim.height
        dst_dim.hidden = dim.hidden
        dst_dim.outlineLevel = dim.outlineLevel

    for row in src_ws.iter_rows():
        for cell in row:
            new_cell = dst_ws.cell(cell.row, cell.column, cell.value)
            if cell.has_style:
                copy_cell_style(cell, new_cell)


def reset_sheet_from_template(wb, template_wb, sheet_name: str):
    if sheet_name in wb.sheetnames:
        sheet_index = wb.sheetnames.index(sheet_name)
        del wb[sheet_name]
    else:
        sheet_index = len(wb.sheetnames)
    ws = wb.create_sheet(sheet_name, sheet_index)
    template_ws = template_wb[sheet_name]
    copy_sheet_layout(template_ws, ws)
    return ws, template_ws


def reset_tabular_sheet_from_template(wb, template_wb, sheet_name: str, rows_to_copy: int = 3):
    if sheet_name in wb.sheetnames:
        sheet_index = wb.sheetnames.index(sheet_name)
        del wb[sheet_name]
    else:
        sheet_index = len(wb.sheetnames)
    ws = wb.create_sheet(sheet_name, sheet_index)
    template_ws = template_wb[sheet_name]

    ws.sheet_view.showGridLines = template_ws.sheet_view.showGridLines
    ws.freeze_panes = template_ws.freeze_panes
    if template_ws.auto_filter and template_ws.auto_filter.ref:
        ws.auto_filter.ref = template_ws.auto_filter.ref
    ws.sheet_format.defaultColWidth = template_ws.sheet_format.defaultColWidth
    ws.sheet_format.defaultRowHeight = template_ws.sheet_format.defaultRowHeight
    ws.sheet_format.zeroHeight = template_ws.sheet_format.zeroHeight
    ws.sheet_properties = copy(template_ws.sheet_properties)
    ws.page_margins = copy(template_ws.page_margins)
    ws.page_setup = copy(template_ws.page_setup)
    ws.print_options = copy(template_ws.print_options)

    for merged in list(template_ws.merged_cells.ranges):
        if merged.max_row <= rows_to_copy:
            ws.merge_cells(str(merged))

    for col_letter, dim in template_ws.column_dimensions.items():
        dst_dim = ws.column_dimensions[col_letter]
        dst_dim.width = dim.width
        dst_dim.hidden = dim.hidden
        dst_dim.bestFit = dim.bestFit
        dst_dim.outlineLevel = dim.outlineLevel

    max_row = min(rows_to_copy, template_ws.max_row)
    for row_idx in range(1, max_row + 1):
        dim = template_ws.row_dimensions[row_idx]
        dst_dim = ws.row_dimensions[row_idx]
        dst_dim.height = dim.height
        dst_dim.hidden = dim.hidden
        dst_dim.outlineLevel = dim.outlineLevel
        for col_idx in range(1, template_ws.max_column + 1):
            src = template_ws.cell(row_idx, col_idx)
            dst = ws.cell(row_idx, col_idx, src.value)
            if src.has_style:
                copy_cell_style(src, dst)
    return ws, template_ws


def clear_value_region(ws, start_row: int, start_col: int) -> None:
    for row_idx in range(start_row, ws.max_row + 1):
        for col_idx in range(start_col, ws.max_column + 1):
            ws.cell(row_idx, col_idx).value = None


def seed_row_from_template(ws, template_ws, target_row: int, template_row: int, start_col: int, end_col: int) -> None:
    if template_row < 1:
        return
    for col_idx in range(start_col, end_col + 1):
        copy_cell_style(template_ws.cell(template_row, col_idx), ws.cell(target_row, col_idx))
    ws.row_dimensions[target_row].height = template_ws.row_dimensions[template_row].height
