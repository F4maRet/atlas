import json

from tests.conftest import PDF, make_docx, make_zip

API = "/api/v1"


# ── Авторизация ──────────────────────────────────────────────────────────────

def test_requires_auth(client):
    client.cookies.clear()
    assert client.get(f"{API}/articles/").status_code == 401
    assert client.get("/uploads/images/x.png").status_code == 401


def test_login_wrong_password_and_cyrillic(client):
    # раньше кириллический пароль ронял hmac.compare_digest → 500
    assert client.post(f"{API}/auth/login", json={"password": "неверно"}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"password": "пароль-теста"}).status_code == 200
    assert client.get(f"{API}/auth/check").json() == {"authenticated": True}


def test_health(client):
    assert client.get("/health").json()["database"] is True


# ── Авторы ───────────────────────────────────────────────────────────────────

def _author(c, name, **kw):
    r = c.post(f"{API}/authors/", json={"full_name": name, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_authors_crud_and_short_name(auth):
    a = _author(auth, "  Иванов   Иван Иванович ")
    assert a["full_name"] == "Иванов Иван Иванович"
    assert a["short_name"] == "Иванов И.И."
    # повторное создание (другой регистр) возвращает существующего
    assert _author(auth, "иванов иван иванович")["id"] == a["id"]
    b = _author(auth, "Петров Пётр")
    r = auth.put(f"{API}/authors/{b['id']}", json={"full_name": "Иванов Иван Иванович"})
    assert r.status_code == 409


# ── Статьи ───────────────────────────────────────────────────────────────────

def test_article_lifecycle(auth):
    a1 = _author(auth, "Сидоров Сидор Сидорович")
    a2 = _author(auth, "Кузнецова Анна")
    col = auth.post(f"{API}/collections/", data={"name": "Сборник 1", "date_start": "2026-01-01",
                                                  "date_end": "2026-02-01"}).json()
    r = auth.post(f"{API}/articles/", data={
        "title": "Статья о связи", "article_type": "ВАК", "collection_id": str(col["id"]),
        "catalog": "2026", "author_ids": json.dumps([a1["id"], a2["id"]]), "lead_author_id": str(a2["id"]),
    }, files={"file": ("статья.pdf", PDF, "application/pdf")})
    assert r.status_code == 201, r.text
    art = r.json()
    assert art["has_file"] and art["collection"]["name"] == "Сборник 1"
    assert [x["id"] for x in art["authors"]] == [a1["id"], a2["id"]]
    assert "file_path" not in art  # серверные пути наружу не отдаются

    # скачивание: имя с кириллицей, содержимое распаковано
    d = auth.get(f"{API}/articles/{art['id']}/download")
    assert d.status_code == 200 and d.content == PDF
    assert "filename*=UTF-8''" in d.headers["content-disposition"]
    p = auth.get(f"{API}/articles/{art['id']}/preview")
    assert p.headers["content-type"] == "application/pdf"

    # очистка полей пустыми строками (раньше было невозможно)
    r = auth.put(f"{API}/articles/{art['id']}", data={"collection_id": "", "catalog": "", "article_type": ""})
    assert r.status_code == 200, r.text
    art2 = r.json()
    assert art2["collection_id"] is None and art2["catalog"] is None and art2["article_type"] is None
    assert art2["lead_author_id"] == a2["id"]

    # удаление главного автора из списка авторов сбрасывает lead_author_id
    art3 = auth.put(f"{API}/articles/{art['id']}", data={"author_ids": json.dumps([a1["id"]])}).json()
    assert art3["lead_author_id"] is None

    # некорректные данные → 400, а не 500
    assert auth.put(f"{API}/articles/{art['id']}", data={"author_ids": "not json"}).status_code == 400
    assert auth.put(f"{API}/articles/{art['id']}", data={"author_ids": "[99999]"}).status_code == 400
    assert auth.put(f"{API}/articles/{art['id']}", data={"collection_id": "99999"}).status_code == 400
    assert auth.put(f"{API}/articles/{art['id']}", data={"title": "   "}).status_code == 400


def test_upload_validation(auth):
    r = auth.post(f"{API}/articles/", data={"title": "X"}, files={"file": ("evil.html", b"<script>", "text/html")})
    assert r.status_code == 400
    big = b"0" * (1024 * 1024 + 10)
    r = auth.post(f"{API}/articles/", data={"title": "X"}, files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_docx_preview_is_sandboxed(auth):
    r = auth.post(f"{API}/articles/", data={"title": "DOCX"},
                  files={"file": ("doc.docx", make_docx("<script>alert(1)</script>"), "application/octet-stream")})
    art = r.json()
    p = auth.get(f"{API}/articles/{art['id']}/preview")
    assert p.status_code == 200
    assert "sandbox" in p.headers["content-security-policy"]
    assert "<script>" not in p.text and "&lt;script&gt;" in p.text


# ── Заключения ───────────────────────────────────────────────────────────────

def test_conclusion_generate_and_download(auth):
    a = _author(auth, "Лаукарт Михаил Сергеевич")
    art = auth.post(f"{API}/articles/", data={"title": "Тестовая статья", "author_ids": json.dumps([a["id"]])}).json()
    r = auth.post(f"{API}/documents/conclusion/{art['id']}/generate")
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["generated_from_template"] and c["original_filename"].startswith("Заключение_Лаукарт_МС_")
    d = auth.get(f"{API}/documents/conclusion/{art['id']}/download")
    assert d.status_code == 200 and d.content[:2] == b"PK"
    html = auth.get(f"{API}/documents/conclusion/{art['id']}/preview").text
    assert "Тестовая статья" in html and "Лаукарт М.С." in html and "автора" in html

    # загруженный PDF скачивается как PDF, а не как .docx
    auth.post(f"{API}/documents/conclusion/{art['id']}", files={"file": ("закл.pdf", PDF, "application/pdf")})
    d = auth.get(f"{API}/documents/conclusion/{art['id']}/download")
    assert d.content == PDF and "pdf" in d.headers["content-disposition"]

    listed = auth.get(f"{API}/articles/{art['id']}").json()
    assert listed["has_conclusion"] and not listed["conclusion_generated"]
    assert auth.delete(f"{API}/articles/{art['id']}").status_code == 204


# ── Рац. предложения + свидетельство ─────────────────────────────────────────

def test_proposal_certificate(auth):
    p = auth.post(f"{API}/proposals/", data={"title": "Рацуха"}).json()
    # раньше папка uploads/certificates не создавалась → 500
    r = auth.post(f"{API}/proposals/{p['id']}/certificate", files={"file": ("св.pdf", PDF, "application/pdf")})
    assert r.status_code == 201, r.text
    r = auth.post(f"{API}/proposals/{p['id']}/certificate", files={"file": ("св2.pdf", PDF, "application/pdf")})
    assert r.status_code == 201
    got = auth.get(f"{API}/proposals/{p['id']}").json()
    assert got["certificate"]["original_filename"] == "св2.pdf"
    assert auth.get(f"{API}/proposals/{p['id']}/certificate/download").content == PDF
    assert auth.delete(f"{API}/proposals/{p['id']}").status_code == 204


# ── ПО ───────────────────────────────────────────────────────────────────────

def test_software_zip_and_documents(auth):
    z = make_zip({"src/main.py": "print('привет')\n", "src/app/util.py": "x = 1\n",
                  "bin/app.exe": b"\x00\x01\x02", "README.md": "# Readme"})
    r = auth.post(f"{API}/software/", data={"title": "Программа"}, files={"file": ("prog.zip", z, "application/zip")})
    assert r.status_code == 201, r.text
    sw = r.json()
    assert sw["files_count"] == 4
    tree = auth.get(f"{API}/software/{sw['id']}/structure").json()["tree"]
    assert [n["name"] for n in tree] == ["bin", "src", "README.md"]  # сначала папки
    fc = auth.get(f"{API}/software/{sw['id']}/file-content", params={"path": "src/main.py"}).json()
    assert fc["content"] == "print('привет')\n" and not fc["binary"]
    assert auth.get(f"{API}/software/{sw['id']}/file-content", params={"path": "bin/app.exe"}).json()["binary"]
    assert auth.get(f"{API}/software/{sw['id']}/file-content", params={"path": "../etc/passwd"}).status_code == 400

    bad = auth.post(f"{API}/software/", data={"title": "Bad"}, files={"file": ("x.zip", b"notzip", "application/zip")})
    assert bad.status_code == 400

    for t in ("annotation", "manual"):
        r = auth.post(f"{API}/software/{sw['id']}/documents", data={"doc_type": t},
                      files={"file": (f"{t}.pdf", PDF, "application/pdf")})
        assert r.status_code == 201, r.text
    # повторная загрузка того же типа заменяет документ
    auth.post(f"{API}/software/{sw['id']}/documents", data={"doc_type": "manual"},
              files={"file": ("manual2.docx", make_docx(), "application/octet-stream")})
    docs = auth.get(f"{API}/software/{sw['id']}").json()["documents"]
    assert len(docs) == 2
    arch = auth.get(f"{API}/software/{sw['id']}/documents/archive")
    assert arch.status_code == 200 and arch.content[:2] == b"PK"


# ── Каталоги ─────────────────────────────────────────────────────────────────

def test_catalogs(auth):
    assert auth.post(f"{API}/catalogs/proposals", json={"name": "Пустой"}).status_code == 201
    p1 = auth.post(f"{API}/proposals/", data={"title": "A", "catalog": "Старый"}).json()
    p2 = auth.post(f"{API}/proposals/", data={"title": "B"}).json()
    names = {c["name"]: c["count"] for c in auth.get(f"{API}/catalogs/proposals").json()}
    assert names["Пустой"] == 0 and names["Старый"] == 1

    auth.post(f"{API}/catalogs/proposals/move", json={"ids": [p2["id"]], "catalog": "Старый"})
    r = auth.put(f"{API}/catalogs/proposals/rename", json={"old_name": "Старый", "new_name": "Новый"})
    assert r.json()["count"] == 2
    auth.delete(f"{API}/catalogs/proposals", params={"name": "Новый"})
    assert auth.get(f"{API}/proposals/{p1['id']}").json()["catalog"] is None
    assert auth.get(f"{API}/catalogs/unknown").status_code == 404


# ── Сборники / конференции ───────────────────────────────────────────────────

def test_collection_clear_fields_and_photo(auth):
    c = auth.post(f"{API}/collections/", data={"name": "С", "university": "ВАС"},
                  files={"photo": ("p.png", b"\x89PNG\r\n\x1a\nxxxx", "image/png")}).json()
    assert c["photo_url"].startswith("/uploads/images/")
    assert auth.get(c["photo_url"]).status_code == 200
    r = auth.put(f"{API}/collections/{c['id']}", data={"university": "", "date_end": "2020-01-01",
                                                        "date_start": "2021-01-01"})
    assert r.status_code == 400  # окончание раньше начала
    r = auth.put(f"{API}/collections/{c['id']}", data={"university": ""})
    assert r.json()["university"] is None
    bad = auth.post(f"{API}/collections/", data={"name": "X"}, files={"photo": ("x.svg", b"<svg/>", "image/svg+xml")})
    assert bad.status_code == 400


def test_conference_filters_and_ics(auth):
    a = _author(auth, "Участник Конференций")
    c = auth.post(f"{API}/conferences/", data={
        "title": "Конф", "date_start": "2026-03-10", "date_end": "2026-03-20",
        "participant_ids": json.dumps([a["id"]]),
    }).json()
    # конференция, идущая в периоде, попадает в выборку (пересечение интервалов)
    ids = [x["id"] for x in auth.get(f"{API}/conferences/", params={"date_from": "2026-03-15"}).json()]
    assert c["id"] in ids
    assert auth.put(f"{API}/conferences/{c['id']}", data={"date_end": ""}).status_code == 200
    assert auth.get(f"{API}/conferences/", params={"date_from": "bad"}).status_code == 400
    ics = auth.get(f"{API}/conferences/{c['id']}/ics")
    assert "BEGIN:VEVENT" in ics.text and "DTSTART;VALUE=DATE:20260310" in ics.text


# ── Авторы: статистика, работы, объединение ──────────────────────────────────

def test_author_stats_works_merge(auth):
    main = _author(auth, "Основной Автор")
    dup = _author(auth, "Основной А.")
    auth.post(f"{API}/articles/", data={"title": "С1", "author_ids": json.dumps([main["id"], dup["id"]])})
    auth.post(f"{API}/articles/", data={"title": "С2", "author_ids": json.dumps([dup["id"]]),
                                        "lead_author_id": str(dup["id"])})
    auth.post(f"{API}/software/", data={"title": "ПО1", "author_ids": json.dumps([dup["id"]])})
    stats = {s["id"]: s for s in auth.get(f"{API}/authors/stats").json()}
    assert stats[dup["id"]]["articles_count"] == 2 and stats[dup["id"]]["total"] == 3

    r = auth.post(f"{API}/authors/{dup['id']}/merge", json={"into_id": main["id"]})
    assert r.status_code == 200, r.text
    works = auth.get(f"{API}/authors/{main['id']}/works").json()
    assert sorted(w["title"] for w in works["articles"]) == ["С1", "С2"]
    assert len(works["software"]) == 1
    assert auth.get(f"{API}/authors/{dup['id']}").status_code == 404


# ── Шаблоны, отчёты, поиск ───────────────────────────────────────────────────

def test_templates(auth):
    lst = auth.get(f"{API}/templates/").json()
    builtin = [t for t in lst if t["doc_type"] == "conclusion" and t["has_file"]]
    assert builtin
    d = auth.get(f"{API}/templates/{builtin[0]['id']}/download")
    assert d.status_code == 200  # раньше кириллическое имя в заголовке → 500
    bad = auth.post(f"{API}/templates/", data={"name": "T", "doc_type": "conclusion"},
                    files={"file": ("t.pdf", PDF, "application/pdf")})
    assert bad.status_code == 400
    assert auth.post(f"{API}/templates/", data={"name": "T", "doc_type": "zzz"}).status_code == 400


def test_reports_and_search(auth):
    dash = auth.get(f"{API}/reports/dashboard").json()
    assert dash["articles"] >= 1 and "attention" in dash and dash["recent"]
    plan = auth.get(f"{API}/reports/publication-plan", params={"type": "software"}).json()
    assert plan and all(i["type"] == "software" for i in plan)
    for url in ("publication-plan/export", "authors-rating/export", "collections-list/export"):
        for fmt in ("csv", "docx"):
            r = auth.get(f"{API}/reports/{url}", params={"format": fmt})
            assert r.status_code == 200, (url, fmt, r.text)
    csv = auth.get(f"{API}/reports/authors-rating/export", params={"format": "csv"}).content
    assert csv.startswith(b"\xef\xbb\xbf")
    hits = auth.get(f"{API}/reports/search", params={"q": "основной"}).json()
    assert any(h["type"] == "author" for h in hits)
    assert any(h["type"] == "article" and h["subtitle"] == "по автору" for h in hits)
