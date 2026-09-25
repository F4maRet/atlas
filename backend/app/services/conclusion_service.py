"""
Генерация заключения об открытом опубликовании по DOCX-шаблону.

Плейсхолдеры в шаблоне:
  [название_статьи] / [имя статьи]     → название статьи
  [ФИО_авторов]                        → авторы в сокращённом виде (Иванов И.И., Петров П.П.)
  [окончание_автор] / [а|ов]           → «а» для одного автора, «ов» для нескольких
  [месяц_загрузки] / [Месяц_загрузки]  → месяц в родительном падеже
  [год_загрузки] / [Год_загрузки]      → год
  [главный_автор]                      → главный автор (или первый в списке)
"""
import io
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from docx import Document

BUILTIN_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "conclusion_template.docx"

MONTHS_GENITIVE = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def abbreviate_name(full_name: str) -> str:
    """'Лаукарт Михаил Сергеевич' → 'Лаукарт М.С.'; уже сокращённые имена не портит."""
    parts = full_name.strip().split()
    if not parts:
        return full_name
    surname, rest = parts[0], parts[1:]
    initials = ""
    for p in rest:
        for chunk in p.split("."):
            chunk = chunk.strip()
            if chunk:
                initials += chunk[0].upper() + "."
    return f"{surname} {initials}".strip()


def conclusion_filename(lead_name: Optional[str], date: Optional[datetime]) -> str:
    """Заключение_Лаукарт_МС_2026-04-12.docx"""
    parts = ["Заключение"]
    if lead_name:
        parts.append(abbreviate_name(lead_name).replace(" ", "_").replace(".", ""))
    if date:
        parts.append(date.strftime("%Y-%m-%d"))
    return "_".join(parts) + ".docx"


def _replace_in_paragraph(para, replacements: dict) -> None:
    """
    Плейсхолдер может быть разбит Word'ом на несколько run'ов. Склеиваем текст
    абзаца, делаем замены и кладём результат в первый run (его форматирование сохраняется).
    """
    runs = para.runs
    if not runs:
        return
    full_text = "".join(r.text for r in runs)
    if "[" not in full_text:
        return
    new_text = full_text
    for placeholder, value in replacements.items():
        new_text = new_text.replace(placeholder, value)
    if new_text == full_text:
        return
    runs[0].text = new_text
    for run in runs[1:]:
        run.text = ""


def _walk_container(container, replacements: dict) -> None:
    for para in container.paragraphs:
        _replace_in_paragraph(para, replacements)
    for table in container.tables:
        for row in table.rows:
            for cell in row.cells:
                _walk_container(cell, replacements)


def build_replacements(article_title: str, author_names: List[str], upload_date: datetime,
                       lead_author_name: Optional[str] = None) -> dict:
    month_name = MONTHS_GENITIVE[upload_date.month]
    year_str = str(upload_date.year)
    abbreviated = [abbreviate_name(n) for n in author_names]
    authors_str = ", ".join(abbreviated) if abbreviated else "—"
    suffix = "а" if len(author_names) == 1 else "ов"
    lead = lead_author_name or (author_names[0] if author_names else None)
    lead_str = abbreviate_name(lead) if lead else "—"
    return {
        "[месяц_загрузки]": month_name, "[Месяц_загрузки]": month_name,
        "[год_загрузки]": year_str, "[Год_загрузки]": year_str,
        "[название_статьи]": article_title, "[имя статьи]": article_title,
        "[ФИО_авторов]": authors_str,
        "[окончание_автор]": suffix, "[а|ов]": suffix,
        "[главный_автор]": lead_str,
    }


def generate_conclusion(
    article_title: str,
    author_names: List[str],
    upload_date: datetime,
    lead_author_name: Optional[str] = None,
    template_bytes: Optional[bytes] = None,
) -> bytes:
    """Заполнить шаблон и вернуть готовый DOCX. Без шаблона — встроенный."""
    source = io.BytesIO(template_bytes) if template_bytes else str(BUILTIN_TEMPLATE_PATH)
    doc = Document(source)
    replacements = build_replacements(article_title, author_names, upload_date, lead_author_name)

    _walk_container(doc, replacements)
    for section in doc.sections:
        for part in (section.header, section.footer, section.first_page_header,
                     section.first_page_footer, section.even_page_header, section.even_page_footer):
            if part is not None and not part.is_linked_to_previous:
                _walk_container(part, replacements)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
