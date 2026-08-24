from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

try:
    import win32com.client
except ImportError:
    raise SystemExit(
        "Dependência ausente.\n"
        "Instale com:\n\n"
        "    pip install pywin32\n"
    )


TASKS = ["cancel_fault", "apointment"]


def normalize_mat(value) -> str:
    if value is None:
        return ""

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    if isinstance(value, int):
        return str(value)

    return str(value).strip()


def normalize_date(value) -> str | None:
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    text = str(value).strip()

    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%d/%m/%Y")
        except ValueError:
            pass

    return None


def read_excel_rows(path: Path) -> list[list]:
    excel = win32com.client.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False

    workbook = None

    try:
        workbook = excel.Workbooks.Open(str(path.resolve()), ReadOnly=True)
        sheet = workbook.Worksheets(1)
        values = sheet.UsedRange.Value

        if values is None:
            return []

        if not isinstance(values, tuple):
            return [[values]]

        rows = []

        for row in values:
            if isinstance(row, tuple):
                rows.append(list(row))
            else:
                rows.append([row])

        return rows

    finally:
        if workbook is not None:
            workbook.Close(SaveChanges=False)

        excel.Quit()


def convert(path: Path) -> list[dict]:
    rows = read_excel_rows(path)

    result = []
    current = None

    for row in rows:
        col_a = row[0] if len(row) > 0 else None
        col_b = row[1] if len(row) > 1 else None

        # Início de um colaborador:
        # RE | 40010 | NOME: | ...
        if str(col_a).strip().upper() == "RE":
            if current and current["days"]:
                current["days"] = sorted(
                    set(current["days"]),
                    key=lambda d: datetime.strptime(d, "%d/%m/%Y"),
                )
                result.append(current)

            current = {
                "mat": normalize_mat(col_b),
                "days": [],
                "tasks": TASKS.copy(),
            }

            continue

        if current is None:
            continue

        date = normalize_date(col_a)

        if date:
            current["days"].append(date)

    if current and current["days"]:
        current["days"] = sorted(
            set(current["days"]),
            key=lambda d: datetime.strptime(d, "%d/%m/%Y"),
        )
        result.append(current)

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="conv.py",
        description="Converte relatório de faltas do HK para JSON do bot."
    )

    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help='Arquivo Excel de entrada. Ex.: -f "agosto.xlsx"',
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Nome/caminho do JSON de saída. Se omitido, gera <arquivo>_data.json.",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.file)

    if not input_path.exists():
        parser.error(f"Arquivo não encontrado: {input_path}")

    if input_path.suffix.lower() not in {".xls", ".xlsx"}:
        parser.error("O arquivo precisa ser .xls ou .xlsx")

    output_path = (
        Path(args.output)
        if args.output
        else input_path.with_name(f"{input_path.stem}_data.json")
    )

    data = convert(input_path)

    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total_days = sum(len(item["days"]) for item in data)

    print("\nConversão concluída!")
    print(f"Arquivo de entrada : {input_path}")
    print(f"Colaboradores      : {len(data)}")
    print(f"Datas              : {total_days}")
    print(f"JSON gerado        : {output_path}\n")


if __name__ == "__main__":
    main()
