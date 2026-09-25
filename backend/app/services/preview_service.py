"""
Предпросмотр и скачивание файлов.

- PDF         → отдаётся inline (браузер показывает во встроенном просмотрщике)
- DOCX        → конвертируется в HTML (python-docx), с картинками
- изображения → inline
- текст       → text/plain (кодировка определяется: UTF-8 / Windows-1251)
- остальное   → HTML-заглушка «предпросмотр недоступен»

HTML предпросмотра отдаётся с CSP `sandbox`: даже если в документ удастся
протащить разметку, скрипты в нём не выполнятся.
"""
import base64
import io
import re
from html import escape
from typing import Optional
from urllib.parse import quote

from docx import Document
from docx.oxml.ns import qn
from fastapi import HTTPException
from fastapi.responses import Response, StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.services.file_service import exists, file_ext, iter_file, read_file_bytes

PREVIEW_CSP = "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'"
TEXT_EXT = {".txt", ".csv", ".md", ".log", ".json", ".xml", ".ini", ".cfg", ".yml", ".yaml"}
IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".gif": "image/gif", ".webp": "image/webp"}
MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".zip": "application/zip",
    **IMAGE_MIME,
}
MAX_TEXT_PREVIEW = 2 * 1024 * 1024
_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")
_SAFE_HREF = re.compile(r"^(https?:|mailto:|#)", re.I)


# ── HTTP helpers ─────────────────────────────────────────────────────────────

def safe_content_disposition(disposition: str, filename: str) -> str:
    """Content-Disposition с поддержкой кириллицы (RFC 6266 / RFC 5987)."""
    ascii_fallback = filename.encode("ascii", "ignore").decode().replace('"', "").strip() or "file"
    if "." in filename and "." not in ascii_fallback:
        ascii_fallback += file_ext(filename)
    return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"


def _ensure(stored: Optional[str]) -> None:
    # Проверяем заранее: ошибка внутри генератора StreamingResponse уже не превратится в 404
    if not exists(stored):
        raise HTTPException(404, "Файл не найден в хранилище")


def download_response(stored: str, filename: str, media_type: Optional[str] = None) -> StreamingResponse:
    _ensure(stored)
    return StreamingResponse(
        iter_file(stored),
        media_type=media_type or MIME.get(file_ext(filename), "application/octet-stream"),
        headers={"Content-Disposition": safe_content_disposition("attachment", filename),
                 "X-Content-Type-Options": "nosniff"},
    )


def _html_response(html: str) -> Response:
    return Response(
        content=html.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Security-Policy": PREVIEW_CSP, "X-Content-Type-Options": "nosniff"},
    )


def unavailable_html(title: str, sub: str) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
        "body{font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;"
        "height:100vh;margin:0;background:#f8f9fa;color:#555;text-align:center}"
        ".box{padding:32px}.icon{font-size:48px;margin-bottom:16px}"
        ".t{font-size:16px;font-weight:600;margin-bottom:8px;color:#333}.s{font-size:13px;color:#888;line-height:1.6}"
        f"</style></head><body><div class=\"box\"><div class=\"icon\">📎</div><div class=\"t\">{escape(title)}</div>"
        f"<div class=\"s\">{escape(sub)}<br>Скачайте файл, чтобы открыть его.</div></div></body></html>"
    )


def decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


async def preview_response(stored: str, filename: str) -> Response:
    _ensure(stored)
    ext = file_ext(filename)
    if ext == ".pdf":
        return StreamingResponse(
            iter_file(stored), media_type="application/pdf",
            headers={"Content-Disposition": safe_content_disposition("inline", filename),
                     "X-Content-Type-Options": "nosniff"},
        )
    if ext in IMAGE_MIME:
        return StreamingResponse(iter_file(stored), media_type=IMAGE_MIME[ext],
                                 headers={"X-Content-Type-Options": "nosniff"})
    if ext == ".docx":
        try:
            raw = await read_file_bytes(stored)
            return _html_response(await run_in_threadpool(docx_to_html, raw))
        except Exception:
            return _html_response(unavailable_html("Предпросмотр недоступен", "Файл не удалось разобрать."))
    if ext in TEXT_EXT:
        raw = await read_file_bytes(stored)
        text = decode_text(raw[:MAX_TEXT_PREVIEW])
        if len(raw) > MAX_TEXT_PREVIEW:
            text += "\n\n… (файл обрезан для предпросмотра)"
        return Response(text.encode("utf-8"), media_type="text/plain; charset=utf-8",
                         headers={"X-Content-Type-Options": "nosniff"})
    return _html_response(unavailable_html(
        "Предпросмотр недоступен", f"Формат {ext or 'без расширения'} не поддерживается для просмотра."))


# ── DOCX → HTML ──────────────────────────────────────────────────────────────

_CSS = """<style>
  * { box-sizing: border-box; }
  body { font-family: 'Times New Roman', Times, serif; font-size: 14pt; margin: 0;
         padding: 28px 44px 40px; color: #1a1a1a; background: #fff; line-height: 1.5; }
  p { margin: 0 0 4px 0; }
  h1,h2,h3,h4 { margin: 14px 0 6px; font-weight: 700; line-height: 1.3; }
  h1 { font-size: 16pt; } h2 { font-size: 15pt; } h3 { font-size: 14pt; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; }
  td, th { border: 1px solid #999; padding: 5px 8px; vertical-align: top; }
  img { max-width: 100%; height: auto; }
  .block-quote { border-left: 3px solid #ccc; margin: 8px 0 8px 12px; padding-left: 12px; color: #444; }
  .page-break { border: none; border-top: 2px dashed #ccc; margin: 16px 0; }
  @media (max-width: 700px) { body { padding: 16px; font-size: 12pt; } }
</style>"""

_HEADINGS = {
    "Heading1": "h1", "heading1": "h1", "1": "h1", "Title": "h1",
    "Heading2": "h2", "heading2": "h2", "2": "h2", "Subtitle": "h2",
    "Heading3": "h3", "heading3": "h3", "3": "h3",
    "Heading4": "h4", "heading4": "h4", "4": "h4",
}
_HIGHLIGHT = {
    "yellow": "#ffff00", "green": "#00ff00", "cyan": "#00ffff", "magenta": "#ff00ff", "blue": "#0000ff",
    "red": "#ff0000", "darkBlue": "#000080", "darkCyan": "#008080", "darkGreen": "#008000",
    "darkMagenta": "#800080", "darkRed": "#800000", "darkYellow": "#808000", "darkGray": "#808080",
    "lightGray": "#c0c0c0",
}


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _int_attr(el, name: str, default: int = 0) -> int:
    try:
        return int(el.get(qn(name), default))
    except (TypeError, ValueError):
        return default


class _Converter:
    def __init__(self, doc):
        self.doc = doc

    def body(self) -> str:
        parts = []
        for block in self.doc.element.body:
            tag = _local(block.tag)
            if tag == "p":
                parts.append(self.paragraph(block))
            elif tag == "tbl":
                parts.append(self.table(block))
        return "".join(parts)

    # paragraphs
    def paragraph(self, p_el) -> str:
        pPr = p_el.find(qn("w:pPr"))
        style = jc = ""
        indent_left = indent_hanging = 0
        sp_before, sp_after = 0.0, 4.0
        is_list = is_quote = False
        if pPr is not None:
            el = pPr.find(qn("w:pStyle"))
            if el is not None:
                style = el.get(qn("w:val"), "")
            el = pPr.find(qn("w:jc"))
            if el is not None:
                jc = el.get(qn("w:val"), "")
            el = pPr.find(qn("w:ind"))
            if el is not None:
                indent_left = _int_attr(el, "w:left") or _int_attr(el, "w:start")
                indent_hanging = _int_attr(el, "w:hanging")
            el = pPr.find(qn("w:spacing"))
            if el is not None:
                sp_before = _int_attr(el, "w:before") / 20
                sp_after = _int_attr(el, "w:after", 80) / 20
            is_list = pPr.find(qn("w:numPr")) is not None
            is_quote = pPr.find(qn("w:pBdr")) is not None

        inline = []
        for child in p_el:
            ct = _local(child.tag)
            if ct == "r":
                inline.append(self.run(child))
            elif ct == "hyperlink":
                inline.append(self.hyperlink(child))
            elif ct in ("ins", "smartTag", "sdt"):
                inline.extend(self.run(r) for r in child.iter(qn("w:r")))
        text = "".join(inline)
        if not text.strip():
            return '<p style="margin:0;min-height:0.8em">&nbsp;</p>'

        css = []
        align = {"center": "center", "right": "right", "end": "right", "both": "justify", "distribute": "justify"}
        if jc in align:
            css.append(f"text-align:{align[jc]}")
        if indent_left > 0:
            css.append(f"margin-left:{indent_left / 20:.1f}pt")
        if indent_hanging > 0 and not is_list:
            css.append(f"text-indent:-{indent_hanging / 20:.1f}pt")
        if sp_before > 0:
            css.append(f"margin-top:{sp_before:.0f}pt")
        if sp_after != 4:
            css.append(f"margin-bottom:{sp_after:.0f}pt")
        style_attr = f' style="{";".join(css)}"' if css else ""

        if is_quote or "Quote" in style:
            return f'<blockquote class="block-quote"{style_attr}>{text}</blockquote>'
        if is_list:
            return f"<p{style_attr}>•&nbsp;{text}</p>"
        tag = _HEADINGS.get(style, "p")
        return f"<{tag}{style_attr}>{text}</{tag}>"

    def hyperlink(self, h_el) -> str:
        href = ""
        r_id = h_el.get(qn("r:id"), "")
        if r_id:
            try:
                href = self.doc.part.rels[r_id].target_ref
            except Exception:
                href = ""
        anchor = h_el.get(qn("w:anchor"))
        if not href and anchor:
            href = "#" + anchor
        text = "".join(self.run(r) for r in h_el if _local(r.tag) == "r")
        if not text:
            return ""
        if not _SAFE_HREF.match(href or ""):
            return text  # javascript:, file: и прочее — показываем просто текстом
        return f'<a href="{escape(href, quote=True)}" rel="noopener noreferrer" style="color:#1a6fcc">{text}</a>'

    # runs
    def run(self, r_el) -> str:
        rPr = r_el.find(qn("w:rPr"))
        bold = italic = underline = strike = sup = sub = False
        css = []
        if rPr is not None:
            b = rPr.find(qn("w:b"))
            bold = b is not None and b.get(qn("w:val"), "true") not in ("0", "false")
            i = rPr.find(qn("w:i"))
            italic = i is not None and i.get(qn("w:val"), "true") not in ("0", "false")
            u = rPr.find(qn("w:u"))
            underline = u is not None and u.get(qn("w:val"), "single") != "none"
            strike = rPr.find(qn("w:strike")) is not None
            sz = rPr.find(qn("w:sz"))
            if sz is not None and _int_attr(sz, "w:val"):
                css.append(f"font-size:{_int_attr(sz, 'w:val') / 2:.0f}pt")
            col = rPr.find(qn("w:color"))
            if col is not None and _HEX.match(col.get(qn("w:val"), "")):
                css.append(f"color:#{col.get(qn('w:val'))}")
            hl = rPr.find(qn("w:highlight"))
            if hl is not None and hl.get(qn("w:val")) in _HIGHLIGHT:
                css.append(f"background:{_HIGHLIGHT[hl.get(qn('w:val'))]}")
            va = rPr.find(qn("w:vertAlign"))
            if va is not None:
                sup = va.get(qn("w:val")) == "superscript"
                sub = va.get(qn("w:val")) == "subscript"

        out = []
        for child in r_el:
            ct = _local(child.tag)
            if ct == "t":
                out.append(escape(child.text or "", quote=False))
            elif ct == "br":
                out.append('<hr class="page-break">' if child.get(qn("w:type")) == "page" else "<br>")
            elif ct == "tab":
                out.append("&emsp;")
            elif ct == "drawing":
                out.append(self.image(child))
            elif ct == "sym":
                try:
                    out.append(escape(chr(int(child.get(qn("w:char"), ""), 16))))
                except ValueError:
                    pass
        text = "".join(out)
        if not text:
            return ""
        if sup:
            text = f"<sup>{text}</sup>"
        if sub:
            text = f"<sub>{text}</sub>"
        if bold:
            text = f"<strong>{text}</strong>"
        if italic:
            text = f"<em>{text}</em>"
        if underline:
            text = f"<u>{text}</u>"
        if strike:
            text = f"<del>{text}</del>"
        if css:
            text = f'<span style="{";".join(css)}">{text}</span>'
        return text

    def image(self, drawing_el) -> str:
        ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
        ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        blip = drawing_el.find(f".//{{{ns_a}}}blip")
        if blip is None:
            return ""
        rid = blip.get(f"{{{ns_r}}}embed")
        try:
            part = self.doc.part.related_parts[rid]
        except Exception:
            return ""
        ctype = getattr(part, "content_type", "")
        if ctype not in ("image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp"):
            return ""
        data = base64.b64encode(part.blob).decode("ascii")
        return f'<img src="data:{ctype};base64,{data}" alt="">'

    # tables
    def table(self, tbl_el) -> str:
        rows = []
        for row_el in tbl_el.findall(qn("w:tr")):
            cells = []
            for cell_el in row_el.findall(qn("w:tc")):
                tc_pr = cell_el.find(qn("w:tcPr"))
                colspan, style = 1, ""
                if tc_pr is not None:
                    vm = tc_pr.find(qn("w:vMerge"))
                    if vm is not None and vm.get(qn("w:val"), "continue") == "continue":
                        continue
                    gs = tc_pr.find(qn("w:gridSpan"))
                    if gs is not None:
                        colspan = max(1, _int_attr(gs, "w:val", 1))
                    shd = tc_pr.find(qn("w:shd"))
                    fill = shd.get(qn("w:fill"), "") if shd is not None else ""
                    if _HEX.match(fill) and fill.lower() != "ffffff":
                        style = f' style="background:#{fill}"'
                content = []
                for child in cell_el:
                    ct = _local(child.tag)
                    if ct == "p":
                        content.append(self.paragraph(child))
                    elif ct == "tbl":
                        content.append(self.table(child))
                cs = f' colspan="{colspan}"' if colspan > 1 else ""
                cells.append(f"<td{cs}{style}>{''.join(content)}</td>")
            if cells:
                rows.append(f"<tr>{''.join(cells)}</tr>")
        return f"<table>{''.join(rows)}</table>"


def docx_to_html(raw: bytes) -> str:
    """DOCX (байты) → самодостаточная HTML-страница."""
    doc = Document(io.BytesIO(raw))
    body = _Converter(doc).body()
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{_CSS}</head><body>{body}</body></html>"
    )
