"""
Convert uploaded files to preview-friendly formats.
- PDF  → served as-is with inline disposition
- DOCX → converted to HTML via python-docx
"""
import gzip
import io
import base64
from html import escape
from urllib.parse import quote

from docx import Document
from docx.oxml.ns import qn


def _read_raw(file_path: str) -> bytes:
    if file_path.endswith(".gz"):
        with gzip.open(file_path, "rb") as f:
            return f.read()
    with open(file_path, "rb") as f:
        return f.read()


def safe_content_disposition(disposition: str, filename: str) -> str:
    """
    Build a Content-Disposition header that handles non-ASCII filenames.
    Uses RFC 5987: filename*=UTF-8''<percent-encoded>
    """
    try:
        filename.encode("latin-1")
        return f'{disposition}; filename="{filename}"'
    except (UnicodeEncodeError, UnicodeDecodeError):
        encoded = quote(filename, safe="")
        return f"{disposition}; filename*=UTF-8''{encoded}"


def docx_to_html(file_path: str) -> str:
    """Convert a .docx (optionally gzip-compressed) to a self-contained HTML string."""
    raw = _read_raw(file_path)
    doc = Document(io.BytesIO(raw))

    css = """<style>
      * { box-sizing: border-box; }
      body {
        font-family: 'Times New Roman', Times, serif;
        font-size: 14pt;
        margin: 0;
        padding: 28px 44px 40px;
        color: #1a1a1a;
        background: #ffffff;
        line-height: 1.5;
      }
      p { margin: 0 0 4px 0; }
      h1,h2,h3,h4,h5,h6 { margin: 14px 0 6px; font-weight: 700; line-height: 1.3; }
      h1 { font-size: 16pt; }
      h2 { font-size: 15pt; }
      h3 { font-size: 14pt; }
      table { border-collapse: collapse; width: 100%; margin: 10px 0; }
      td, th { border: 1px solid #999; padding: 5px 8px; vertical-align: top; }
      th { background: #f0f0f0; font-weight: 600; }
      img { max-width: 100%; height: auto; display: block; margin: 8px 0; }
      .block-quote { border-left: 3px solid #ccc; margin: 8px 0 8px 12px; padding-left: 12px; color: #444; }
      .list-item { padding-left: 24px; position: relative; margin: 2px 0; }
      .list-item::before { position: absolute; left: 8px; }
    </style>"""

    body_parts = []
    for block in doc.element.body:
        tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag
        if tag == "p":
            body_parts.append(_parse_paragraph(block, doc))
        elif tag == "tbl":
            body_parts.append(_parse_table(block, doc))

    body_html = "".join(body_parts)
    return (
        f"<!DOCTYPE html><html><head>"
        f'<meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{css}</head>"
        f"<body>{body_html}</body></html>"
    )


def _get_style_name(p_el) -> str:
    pPr = p_el.find(qn("w:pPr"))
    if pPr is not None:
        el = pPr.find(qn("w:pStyle"))
        if el is not None:
            return el.get(qn("w:val"), "")
    return ""


def _parse_paragraph(p_el, doc=None) -> str:
    pPr = p_el.find(qn("w:pPr"))
    style_name = ""
    jc = ""
    indent_left = 0
    indent_hanging = 0
    sp_before = 0
    sp_after = 4
    num_id = None
    num_ilvl = 0
    is_blockquote = False

    if pPr is not None:
        el = pPr.find(qn("w:pStyle"))
        if el is not None:
            style_name = el.get(qn("w:val"), "")

        el = pPr.find(qn("w:jc"))
        if el is not None:
            jc = el.get(qn("w:val"), "")

        el = pPr.find(qn("w:ind"))
        if el is not None:
            try:
                l = el.get(qn("w:left"), "0")
                indent_left = int(l) if l else 0
            except Exception:
                pass
            try:
                h = el.get(qn("w:hanging"), "0")
                indent_hanging = int(h) if h else 0
            except Exception:
                pass

        el = pPr.find(qn("w:spacing"))
        if el is not None:
            try:
                b = el.get(qn("w:before"), "0")
                sp_before = int(b) / 20 if b else 0
            except Exception:
                pass
            try:
                a = el.get(qn("w:after"), "0")
                sp_after = int(a) / 20 if a else 4
            except Exception:
                pass

        # List / numbering
        numPr = pPr.find(qn("w:numPr"))
        if numPr is not None:
            el_id = numPr.find(qn("w:numId"))
            el_ilvl = numPr.find(qn("w:ilvl"))
            if el_id is not None:
                num_id = el_id.get(qn("w:val"))
            if el_ilvl is not None:
                try:
                    num_ilvl = int(el_ilvl.get(qn("w:val"), "0"))
                except Exception:
                    pass

        # Blockquote detection
        if pPr.find(qn("w:pBdr")) is not None:
            is_blockquote = True

    # Heading detection
    heading_map = {
        "Heading1": "h1", "heading1": "h1", "1": "h1",
        "Heading2": "h2", "heading2": "h2", "2": "h2",
        "Heading3": "h3", "heading3": "h3", "3": "h3",
        "Heading4": "h4", "heading4": "h4",
        "Title": "h1", "Subtitle": "h2",
    }
    html_tag = heading_map.get(style_name, "p")

    # Build inline content
    inline = []
    for child in p_el:
        ct = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if ct == "r":
            inline.append(_parse_run(child))
        elif ct == "hyperlink":
            r_id = child.get(qn("r:id"), "")
            href = "#"
            if r_id and doc is not None:
                try:
                    href = doc.part.rels[r_id].target_ref
                except Exception:
                    href = "#"
            link_parts = []
            for r in child:
                rt = r.tag.split("}")[-1] if "}" in r.tag else r.tag
                if rt == "r":
                    link_parts.append(_parse_run(r))
            link_text = "".join(link_parts)
            if link_text:
                inline.append(
                    f'<a href="{escape(href, quote=True)}" target="_blank" '
                    f'rel="noopener noreferrer" style="color:#1a6fcc">{link_text}</a>'
                )
        elif ct == "bookmarkStart":
            pass

    text = "".join(inline)
    if not text.strip():
        return '<p style="margin:0;min-height:0.8em">&nbsp;</p>'

    # Build CSS
    align_map = {"center": "center", "right": "right", "both": "justify", "distribute": "justify"}
    align_css = f"text-align:{align_map[jc]};" if jc in align_map else ""

    margin_left_pt = indent_left / 20
    hanging_pt = indent_hanging / 20
    margin_css = ""
    text_indent_css = ""
    if margin_left_pt > 0:
        margin_css = f"margin-left:{margin_left_pt:.1f}pt;"
    if hanging_pt > 0:
        text_indent_css = f"text-indent:-{hanging_pt:.1f}pt;"

    sp_css = ""
    if sp_before > 0:
        sp_css += f"margin-top:{sp_before:.0f}pt;"
    if sp_after != 4:
        sp_css += f"margin-bottom:{sp_after:.0f}pt;"

    style_attr = f"{align_css}{margin_css}{text_indent_css}{sp_css}"

    if is_blockquote or (style_name and "Quote" in style_name):
        return f'<blockquote class="block-quote" style="{style_attr}">{text}</blockquote>'

    if num_id is not None:
        list_indent = f"padding-left:{max(24, margin_left_pt + 24):.0f}pt;"
        return f'<p class="list-item" style="{list_indent}{align_css}{sp_css}">• {text}</p>'

    if style_attr:
        return f'<{html_tag} style="{style_attr}">{text}</{html_tag}>'
    return f'<{html_tag}>{text}</{html_tag}>'


def _parse_run(r_el) -> str:
    rPr = r_el.find(qn("w:rPr"))
    bold = italic = underline = strike = False
    font_size = color = highlight = ""
    is_superscript = is_subscript = False

    if rPr is not None:
        bold = rPr.find(qn("w:b")) is not None
        italic = rPr.find(qn("w:i")) is not None
        underline = rPr.find(qn("w:u")) is not None and \
                    (rPr.find(qn("w:u")) is not None and
                     rPr.find(qn("w:u")).get(qn("w:val"), "single") != "none")
        strike = rPr.find(qn("w:strike")) is not None

        sz = rPr.find(qn("w:sz"))
        if sz is not None:
            try:
                font_size = f"font-size:{int(sz.get(qn('w:val'), 28)) / 2:.0f}pt;"
            except Exception:
                pass

        col = rPr.find(qn("w:color"))
        if col is not None:
            val = col.get(qn("w:val"), "")
            if val and val.lower() != "auto":
                color = f"color:#{val};"

        hl = rPr.find(qn("w:highlight"))
        if hl is not None:
            hl_color_map = {
                "yellow": "#ffff00", "green": "#00ff00", "cyan": "#00ffff",
                "magenta": "#ff00ff", "blue": "#0000ff", "red": "#ff0000",
                "darkBlue": "#000080", "darkCyan": "#008080", "darkGreen": "#008000",
                "darkMagenta": "#800080", "darkRed": "#800000", "darkYellow": "#808000",
                "darkGray": "#808080", "lightGray": "#c0c0c0",
            }
            hl_val = hl.get(qn("w:val"), "")
            if hl_val in hl_color_map:
                highlight = f"background:{hl_color_map[hl_val]};"

        vert = rPr.find(qn("w:vertAlign"))
        if vert is not None:
            v = vert.get(qn("w:val"), "")
            if v == "superscript":
                is_superscript = True
            elif v == "subscript":
                is_subscript = True

    texts = []
    for child in r_el:
        ct = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if ct == "t":
            t = (child.text or "")
            t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            texts.append(t)
        elif ct == "br":
            br_type = child.get(qn("w:type"), "")
            if br_type == "page":
                texts.append('<hr style="border:none;border-top:2px dashed #ccc;margin:16px 0">')
            else:
                texts.append("<br>")
        elif ct == "tab":
            texts.append("&nbsp;&nbsp;&nbsp;&nbsp;")
        elif ct == "drawing":
            # Try to extract inline image
            img_html = _extract_image(child)
            if img_html:
                texts.append(img_html)
        elif ct == "sym":
            char = child.get(qn("w:char"), "")
            if char:
                try:
                    texts.append(chr(int(char, 16)))
                except Exception:
                    pass

    text = "".join(texts)
    if not text:
        return ""

    if is_superscript:
        text = f"<sup>{text}</sup>"
    if is_subscript:
        text = f"<sub>{text}</sub>"
    if bold:
        text = f"<strong>{text}</strong>"
    if italic:
        text = f"<em>{text}</em>"
    if underline:
        text = f'<span style="text-decoration:underline">{text}</span>'
    if strike:
        text = f"<del>{text}</del>"

    style = f"{font_size}{color}{highlight}"
    if style:
        text = f'<span style="{style}">{text}</span>'
    return text


def _extract_image(drawing_el) -> str:
    """Try to extract an image from a w:drawing element and return an <img> tag."""
    try:
        # Find blip element that has the image relationship ID
        ns_a = "http://schemas.openxmlformats.org/drawingml/2006/main"
        ns_r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        blip = drawing_el.find(".//{%s}blip" % ns_a)
        if blip is None:
            return ""
        # We can't resolve relationships here without doc context, skip
        return ""
    except Exception:
        return ""


def _parse_table(tbl_el, doc=None) -> str:
    rows = []
    tbl_pr = tbl_el.find(qn("w:tblPr"))
    has_borders = True

    for row_el in tbl_el.findall(qn("w:tr")):
        cells = []
        for cell_el in row_el.findall(qn("w:tc")):
            # Check for vertical merge
            tc_pr = cell_el.find(qn("w:tcPr"))
            v_merge = None
            colspan = 1
            cell_style = ""
            if tc_pr is not None:
                vm = tc_pr.find(qn("w:vMerge"))
                if vm is not None:
                    v_merge = vm.get(qn("w:val"), "continue")
                gs = tc_pr.find(qn("w:gridSpan"))
                if gs is not None:
                    try:
                        colspan = int(gs.get(qn("w:val"), "1"))
                    except Exception:
                        pass
                # Background color
                shd = tc_pr.find(qn("w:shd"))
                if shd is not None:
                    fill = shd.get(qn("w:fill"), "")
                    if fill and fill.lower() not in ("auto", "ffffff", ""):
                        cell_style = f'background:#{fill};'

            if v_merge == "continue":
                continue

            cell_parts = [_parse_paragraph(p, doc) for p in cell_el.findall(qn("w:p"))]
            cs_attr = f' colspan="{colspan}"' if colspan > 1 else ""
            st_attr = f' style="{cell_style}"' if cell_style else ""
            cells.append(f"<td{cs_attr}{st_attr}>{''.join(cell_parts)}</td>")
        if cells:
            rows.append(f"<tr>{''.join(cells)}</tr>")
    return f'<table style="border-collapse:collapse;width:100%;margin:8px 0">{"".join(rows)}</table>'
