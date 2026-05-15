"""
app.py — Flet-интерфейс «Скидочный сыщик».

Страницы:
  1. Вход / Регистрация
  2. Главная (поиск + карточки товаров)
  3. Мой список (избранное из БД)

Запуск:  python frontend/app.py
"""

import flet as ft
import httpx
import threading
import time

# ── Адрес бэкенда ──
API_BASE = "http://127.0.0.1:8000"

# ── Цветовая палитра ──
BG_COLOR       = "#0D1117"          # почти чёрный фон
SURFACE_COLOR  = "#161B22"          # карточки/панели
BORDER_COLOR   = "#30363D"          # рамки
ACCENT         = "#7C3AED"          # фиолетовый акцент
ACCENT_LIGHT   = "#A855F7"
GREEN          = "#22C55E"          # цена со скидкой
RED            = "#F87171"          # ошибки
TEXT_PRIMARY   = "#F0F6FC"          # главный текст
TEXT_SECONDARY = "#8B949E"          # второстепенный
GOLD           = "#F59E0B"          # «В избранное»


# ════════════════════════════════════════════════════════════
#  Вспомогательные функции
# ════════════════════════════════════════════════════════════

# ── HTTP-клиент: trust_env=False чтобы обойти корпоративный прокси
#    (иначе httpx гонит даже localhost через системный HTTP_PROXY)
_http_client = httpx.Client(
    trust_env=False,          # не читать HTTP_PROXY / HTTPS_PROXY из env
    timeout=10,
)


def api(method: str, path: str, token: str = None, **kwargs):
    """Обёртка над httpx — выполняет запрос к API."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = _http_client.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
            **kwargs,
        )
        return resp
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.TimeoutException):
        return None


def safe_json(resp) -> dict:
    """Безопасно парсит JSON из ответа; при ошибке возвращает {}."""
    try:
        return resp.json()
    except Exception:
        return {}


def discount_pct(current: float, old: float) -> int:
    """Считает процент скидки."""
    if old and old > current:
        return int((1 - current / old) * 100)
    return 0


# ════════════════════════════════════════════════════════════
#  Компоненты
# ════════════════════════════════════════════════════════════

def make_text_field(label: str, password: bool = False, ref=None) -> ft.TextField:
    """Стилизованное текстовое поле."""
    return ft.TextField(
        ref=ref,
        label=label,
        password=password,
        can_reveal_password=password,
        border_color=BORDER_COLOR,
        focused_border_color=ACCENT,
        label_style=ft.TextStyle(color=TEXT_SECONDARY),
        text_style=ft.TextStyle(color=TEXT_PRIMARY),
        cursor_color=ACCENT,
        bgcolor=SURFACE_COLOR,
        border_radius=10,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
    )


def make_button(text: str, on_click, primary: bool = True, icon=None) -> ft.ElevatedButton:
    """Кнопка с акцентным или второстепенным стилем."""
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ACCENT if primary else SURFACE_COLOR,
            color=TEXT_PRIMARY,
            overlay_color="#267C3AED",  # ~15% opacity accent
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
        ),
    )
def star_row(rating: float, reviews: int) -> ft.Row:
    """Строка со звёздами и кол-вом отзывов."""
    stars = []
    for i in range(1, 6):
        color = GOLD if rating >= (i - 0.25) else ("#88F59E0B" if rating >= (i - 0.75) else BORDER_COLOR)
        stars.append(ft.Icon(ft.icons.STAR, color=color, size=13))
    return ft.Row(
        spacing=2,
        controls=[
            *stars,
            ft.Text(f"{rating:.1f}  ({reviews:,})".replace(",", " "),
                    color=TEXT_SECONDARY, size=11),
        ],
    )


def product_card(item: dict, on_favorite, on_cancel, page: ft.Page,
                 already_added: bool = False, fav_id: int = None) -> ft.Container:
    """Карточка товара: изображение, название, цена, кнопки действий.
    Вся карточка кликабельна (открывает URL).
    Кнопка избранного — переключатель: добавить / отменить.
    """
    pct = discount_pct(item["current_price"], item.get("old_price", 0))
    has_discount = pct > 0
    marketplace_colors = {"WB": "#CB11AB", "Ozon": "#005BFF", "Ya": "#FFCC00"}
    mp_color = marketplace_colors.get(item.get("marketplace_name", "WB"), ACCENT)
    rating_widget = star_row(item["rating"], item.get("reviews_count") or 0) if item.get("rating") else None

    saved_id: dict = {"value": fav_id}   # id из БД (None если не знаем)
    is_added: dict = {"value": already_added}

    # ── Кнопка «В избранное» / «Добавлено ✓ (отмена)» ──
    fav_btn = ft.ElevatedButton(
        text="В избранном ✓" if already_added else "В избранное",
        icon=ft.icons.STAR if already_added else ft.icons.STAR_OUTLINE,
        expand=True,
        style=ft.ButtonStyle(
            bgcolor="#1F22C55E" if already_added else "#1FF59E0B",
            color=GREEN if already_added else GOLD,
            overlay_color="#33F59E0B",
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=8, vertical=6),
        ),
    )

    def handle_fav(e):
        e.stop_propagation = True  # не прокидываем клик на карточку
        if is_added["value"]:
            # Повторное нажатие — отмена
            if on_cancel:
                # Если id не знаем — ищем по URL
                fav_item_id = saved_id["value"]
                if not fav_item_id:
                    fav_item_id = on_cancel(item["url"], lookup=True)
                if fav_item_id:
                    on_cancel(fav_item_id)
            fav_btn.text = "В избранное"
            fav_btn.icon = ft.icons.STAR_OUTLINE
            fav_btn.style = ft.ButtonStyle(
                bgcolor="#1FF59E0B", color=GOLD, overlay_color="#33F59E0B",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=8, vertical=6),
            )
            saved_id["value"] = None
            is_added["value"] = False
            page.update()
        else:
            result = on_favorite(item)
            if result:
                fav_btn.text = "В избранном ✓"
                fav_btn.icon = ft.icons.STAR
                fav_btn.style = ft.ButtonStyle(
                    bgcolor="#1F22C55E", color=GREEN, overlay_color="#33F59E0B",
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                )
                if isinstance(result, dict):
                    saved_id["value"] = result.get("id")
                is_added["value"] = True
                page.update()

    fav_btn.on_click = handle_fav

    # ── Строка цены ──
    price_row_controls = [
        ft.Text(
            f"₽ {item['current_price']:,.0f}".replace(",", " "),
            color=GREEN if has_discount else TEXT_PRIMARY,
            size=16, weight=ft.FontWeight.BOLD,
        ),
    ]
    if has_discount:
        price_row_controls += [
            ft.Text(
                f"₽ {item['old_price']:,.0f}".replace(",", " "),
                color=TEXT_SECONDARY, size=11,
                style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH),
            ),
            ft.Container(
                content=ft.Text(f"-{pct}%", color="white", size=10, weight=ft.FontWeight.BOLD),
                bgcolor=GREEN, border_radius=5,
                padding=ft.padding.symmetric(horizontal=5, vertical=1),
            ),
        ]

    card_inner = ft.Column(
        spacing=0, tight=True,
        controls=[
            # ── Изображение ──
            ft.Container(
                height=200,
                content=ft.Stack(
                    controls=[
                        ft.Image(
                            src=item.get("image_url") or "https://via.placeholder.com/300x145",
                            width=310, height=200,
                            fit=ft.ImageFit.COVER,
                            error_content=ft.Container(
                                bgcolor="#1a1a2e", width=310, height=200,
                                content=ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED, color=TEXT_SECONDARY),
                            ),
                        ),
                        ft.Container(
                            content=ft.Text(
                                item.get("marketplace_name", ""),
                                color="white", size=10, weight=ft.FontWeight.BOLD,
                            ),
                            bgcolor=mp_color,
                            border_radius=ft.border_radius.only(bottom_right=7),
                            padding=ft.padding.symmetric(horizontal=7, vertical=3),
                            top=0, left=0,
                        ),
                        # ── Подсказка «открыть» поверх изображения ──
                        ft.Container(
                            right=6, bottom=6,
                            content=ft.Icon(ft.icons.OPEN_IN_NEW, color="white", size=15),
                            bgcolor="#88000000",
                            border_radius=6,
                            padding=ft.padding.all(3),
                        ),
                    ],
                ),
            ),
            # ── Контент ──
            ft.Container(
                padding=ft.padding.all(12),
                content=ft.Column(
                    spacing=6, tight=True,
                    controls=[
                        ft.Text(
                            item["title"],
                            color=TEXT_PRIMARY, size=12,
                            weight=ft.FontWeight.W_500,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        *([ rating_widget ] if rating_widget else []),
                        ft.Row(
                            controls=price_row_controls,
                            wrap=True, spacing=6, run_spacing=2,
                        ),
                        ft.Row(controls=[fav_btn], tight=True),
                    ],
                ),
            ),
        ],
    )

    return ft.Container(
        border_radius=14,
        bgcolor=SURFACE_COLOR,
        border=ft.border.all(1, BORDER_COLOR),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        on_click=lambda e: page.launch_url(item["url"]),
        ink=True,
        content=card_inner,
    )


def favorite_card(item: dict, on_delete, page: ft.Page) -> ft.Container:
    """Карточка товара в разделе «Мой список».
    Клик раскрывает/сворачивает панель истории цен.
    История: каждая запись сравнивается с предыдущей — видно дорожает/дешевеет.
    Карточка: итоговое изменение цены за всё время (первая → текущая).
    """
    current_price = item["current_price"]
    history = item.get("price_history") or []
    expanded: dict = {"value": False}

    # ── Итоговое изменение (первая цена из истории → текущая) ──
    first_price = history[0]["price"] if history else None
    total_diff  = (current_price - first_price) if first_price and first_price != current_price else None
    total_pct   = int(total_diff / first_price * 100) if (total_diff and first_price) else None

    # ── Блок цены ──
    price_color = (
        GREEN if (total_diff is not None and total_diff < 0)
        else (RED if (total_diff is not None and total_diff > 0) else TEXT_PRIMARY)
    )
    price_controls = [
        ft.Text(
            f"₽ {current_price:,.0f}".replace(",", " "),
            color=price_color, size=18, weight=ft.FontWeight.BOLD,
        ),
    ]
    if total_diff is not None:
        sign = "↓" if total_diff < 0 else "↑"
        badge_color = GREEN if total_diff < 0 else RED
        badge = f"{sign} {abs(total_pct)}%  {abs(total_diff):,.0f} ₽".replace(",", " ")
        price_controls.append(
            ft.Container(
                content=ft.Text(badge, color="white", size=10, weight=ft.FontWeight.BOLD),
                bgcolor=badge_color, border_radius=5,
                padding=ft.padding.symmetric(horizontal=5, vertical=2),
            )
        )
        price_controls.append(
            ft.Text(f"от ₽ {first_price:,.0f}".replace(",", " "),
                    color=TEXT_SECONDARY, size=10, italic=True)
        )
    price_col = ft.Column(
        spacing=3, tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.END,
        controls=price_controls,
    )

    # ── Стрелочка ──
    arrow_icon = ft.Icon(ft.icons.KEYBOARD_ARROW_DOWN, color=TEXT_SECONDARY, size=20)

    # ── Строки истории цен с трендом ──
    def make_history_row(record: dict, prev_price):
        price_val = record.get("price", 0)
        date_str  = (record.get("checked_at") or "")[:10]

        if prev_price is None:
            trend = ft.Text("старт", color=TEXT_SECONDARY, size=10, italic=True)
        else:
            diff = price_val - prev_price
            if abs(diff) < 0.01:
                trend = ft.Text("без изм.", color=TEXT_SECONDARY, size=10)
            else:
                sign_  = "↓ дешевеет" if diff < 0 else "↑ дорожает"
                clr    = GREEN if diff < 0 else RED
                pct_v  = int(abs(diff) / prev_price * 100) if prev_price else 0
                label  = f"{sign_}  {abs(diff):,.0f} ₽  ({pct_v}%)".replace(",", " ")
                trend  = ft.Container(
                    content=ft.Text(label, color="white", size=10, weight=ft.FontWeight.BOLD),
                    bgcolor=clr, border_radius=4,
                    padding=ft.padding.symmetric(horizontal=5, vertical=1),
                )

        return ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(date_str, color=TEXT_SECONDARY, size=11, width=90, no_wrap=True),
                ft.Text(f"₽ {price_val:,.0f}".replace(",", " "),
                        color=TEXT_PRIMARY, size=12,
                        weight=ft.FontWeight.W_500, width=90),
                trend,
            ],
        )

    if history:
        rows = [make_history_row(r, history[i - 1]["price"] if i > 0 else None)
                for i, r in enumerate(history)]
        history_content = ft.Column(spacing=5, tight=True, controls=rows)
    else:
        history_content = ft.Text("История цен пока не накоплена",
                                  color=TEXT_SECONDARY, size=12, italic=True)

    history_panel = ft.Container(
        visible=False,
        bgcolor="#0a0f16",
        border=ft.border.only(top=ft.BorderSide(1, BORDER_COLOR)),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        content=ft.Column(
            spacing=8, tight=True,
            controls=[
                ft.Row(spacing=6, controls=[
                    ft.Icon(ft.icons.HISTORY, color=ACCENT_LIGHT, size=14),
                    ft.Text("История цен", color=ACCENT_LIGHT,
                            size=12, weight=ft.FontWeight.BOLD),
                ]),
                ft.Divider(color=BORDER_COLOR, height=1),
                history_content,
            ],
        ),
    )

    card_row = ft.Row(
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(content=arrow_icon, width=28, alignment=ft.alignment.center),
            ft.Image(
                src=item.get("image_url") or "https://via.placeholder.com/72",
                width=72, height=72, fit=ft.ImageFit.COVER, border_radius=8,
            ),
            ft.Column(
                expand=True, spacing=3, tight=True,
                controls=[
                    ft.Text(item["title"], color=TEXT_PRIMARY, size=13,
                            weight=ft.FontWeight.W_500, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    *([ star_row(item["rating"], item.get("reviews_count") or 0) ]
                      if item.get("rating") is not None else []),
                    ft.Container(
                        content=ft.Text(item.get("marketplace_name", ""),
                                        color="white", size=10, weight=ft.FontWeight.BOLD),
                        bgcolor={
                            "WB": "#CB11AB", "Ozon": "#005BFF", "Ya": "#FFCC00"
                        }.get(item.get("marketplace_name", ""), ACCENT),
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    ),
                ],
            ),
            price_col,
            ft.Row(
                spacing=0, tight=True,
                controls=[
                    ft.IconButton(
                        icon=ft.icons.OPEN_IN_NEW, icon_color=TEXT_SECONDARY,
                        tooltip="Открыть на сайте", icon_size=20,
                        on_click=lambda e, u=item["url"]: page.launch_url(u),
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE_OUTLINE, icon_color=RED,
                        tooltip="Удалить из списка", icon_size=20,
                        on_click=lambda e, i=item: on_delete(i),
                    ),
                ],
            ),
        ],
    )

    outer: list = [{}]

    def toggle_history(e):
        expanded["value"] = not expanded["value"]
        history_panel.visible = expanded["value"]
        arrow_icon.name = (
            ft.icons.KEYBOARD_ARROW_UP if expanded["value"]
            else ft.icons.KEYBOARD_ARROW_DOWN
        )
        outer[0]["ref"].update()

    card_container = ft.Container(
        border_radius=12,
        bgcolor=SURFACE_COLOR,
        border=ft.border.all(1, BORDER_COLOR),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        on_click=toggle_history,
        ink=True,
        content=ft.Column(
            spacing=0, tight=True,
            controls=[
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    content=card_row,
                ),
                history_panel,
            ],
        ),
    )
    outer[0]["ref"] = card_container
    return card_container



# ════════════════════════════════════════════════════════════
#  Главная функция Flet
# ════════════════════════════════════════════════════════════

def main(page: ft.Page):
    page.title = "Скидочный сыщик"
    page.bgcolor = BG_COLOR
    page.window_width = 1100
    page.window_height = 780
    page.window_min_width = 800
    page.padding = 0
    page.fonts = {
        "Inter": "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2"
    }
    page.theme = ft.Theme(font_family="Inter")

    # ── Состояние приложения ──
    token_ref = {"value": None}
    snack_ref = ft.SnackBar(content=ft.Text(""), bgcolor=SURFACE_COLOR)
    page.overlay.append(snack_ref)

    def show_snack(msg: str, error: bool = False):
        snack_ref.content = ft.Text(msg, color=RED if error else GREEN)
        snack_ref.bgcolor = SURFACE_COLOR
        snack_ref.open = True
        page.update()

    # ════════════════════════════════════════════
    #  СТРАНИЦА 1: ВХОД / РЕГИСТРАЦИЯ
    # ════════════════════════════════════════════

    email_field    = make_text_field("Email")
    password_field = make_text_field("Пароль", password=True)
    auth_error     = ft.Text("", color=RED, size=13)
    auth_mode      = {"reg": False}   # False = вход, True = регистрация

    def validate_form(email: str, pwd: str) -> str | None:
        """Возвращает текст ошибки или None если всё ок."""
        import re
        if not email or not pwd:
            return "Заполните все поля"
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return "Введите корректный email (example@mail.com)"
        if len(pwd) < 4:
            return "Пароль должен быть не менее 4 символов"
        return None

    def do_auth(e):
        email = email_field.value.strip()
        pwd   = password_field.value.strip()

        # ── Валидация на клиенте ──
        err = validate_form(email, pwd)
        if err:
            auth_error.value = err
            auth_error.color = RED
            page.update()
            return

        auth_error.value = ""
        page.update()

        if auth_mode["reg"]:
            resp = api("POST", "/auth/register", json={"email": email, "password": pwd})
            if resp is None:
                auth_error.value = "⚠ Нет связи с сервером. Запущен ли бэкенд?"
                auth_error.color = RED
                page.update()
                return
            if resp.status_code == 201:
                auth_mode["reg"] = False
                auth_error.value = "✓ Аккаунт создан! Войдите."
                auth_error.color = GREEN
                toggle_mode_text.value = "Уже есть аккаунт? Войти"
                auth_btn.text = "Войти"
                page.update()
                return
            else:
                auth_error.value = safe_json(resp).get("detail", "Ошибка регистрации")
                auth_error.color = RED
                page.update()
                return

        # ── Вход ──
        resp = api(
            "POST", "/auth/login",
            data={"username": email, "password": pwd},
        )
        if resp is None:
            auth_error.value = "⚠ Нет связи с сервером. Запущен ли бэкенд?"
            auth_error.color = RED
            page.update()
            return
        if resp.status_code == 200:
            token_ref["value"] = safe_json(resp).get("access_token")
            page.go("/home")
        else:
            auth_error.value = safe_json(resp).get("detail", "Неверный email или пароль")
            auth_error.color = RED
            page.update()

    auth_btn = make_button("Войти", do_auth)

    def toggle_mode(e):
        auth_mode["reg"] = not auth_mode["reg"]
        if auth_mode["reg"]:
            auth_btn.text = "Зарегистрироваться"
            toggle_mode_text.value = "Уже есть аккаунт? Войти"
        else:
            auth_btn.text = "Войти"
            toggle_mode_text.value = "Нет аккаунта? Зарегистрироваться"
        auth_error.value = ""
        page.update()

    toggle_mode_text = ft.TextButton(
        "Нет аккаунта? Зарегистрироваться",
        on_click=toggle_mode,
        style=ft.ButtonStyle(color=ACCENT_LIGHT),
    )

    auth_page = ft.View(
        route="/",
        bgcolor=BG_COLOR,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=420,
                padding=ft.padding.all(40),
                border_radius=20,
                bgcolor=SURFACE_COLOR,
                border=ft.border.all(1, BORDER_COLOR),
                shadow=ft.BoxShadow(
                    blur_radius=40,
                    color="#667C3AED",  # ~40% opacity accent
                    offset=ft.Offset(0, 8),
                ),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=12,
                            controls=[
                                ft.Icon(ft.icons.SEARCH, color=ACCENT, size=32),
                                ft.Text(
                                    "Скидочный сыщик",
                                    size=26,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_PRIMARY,
                                ),
                            ],
                        ),
                        ft.Text("Войди, чтобы искать скидки", color=TEXT_SECONDARY, size=14),
                        ft.Divider(color=BORDER_COLOR, height=1),
                        email_field,
                        password_field,
                        auth_error,
                        auth_btn,
                        toggle_mode_text,
                    ],
                ),
            ),
        ],
    )

    # ════════════════════════════════════════════
    #  СТРАНИЦА 2: ГЛАВНАЯ (поиск)
    # ════════════════════════════════════════════

    search_field   = ft.TextField(
        hint_text="Поиск товаров на WB, Ozon, Яндекс...",
        expand=True,
        border_color=BORDER_COLOR,
        focused_border_color=ACCENT,
        hint_style=ft.TextStyle(color=TEXT_SECONDARY),
        text_style=ft.TextStyle(color=TEXT_PRIMARY),
        cursor_color=ACCENT,
        bgcolor=SURFACE_COLOR,
        border_radius=12,
        content_padding=ft.padding.symmetric(horizontal=18, vertical=16),
        prefix_icon=ft.icons.SEARCH,
    )
    results_grid   = ft.GridView(
        expand=True,
        max_extent=300,
        spacing=16,
        run_spacing=16,
        child_aspect_ratio=0.8,
    )
    search_status  = ft.Text("", color=TEXT_SECONDARY, size=14)
    loading_ring   = ft.ProgressRing(color=ACCENT, visible=False)

    def do_search(e=None):
        q = search_field.value.strip()
        if not q:
            return
        loading_ring.visible = True
        search_status.value = ""
        results_grid.controls.clear()
        page.update()

        resp = api("GET", f"/search?q={q}", token=token_ref["value"])
        loading_ring.visible = False

        if resp is None:
            search_status.value = "⚠ Не удалось подключиться к серверу"
            page.update()
            return
        if resp.status_code == 401:
            page.go("/")
            return
        if resp.status_code != 200:
            search_status.value = "Ошибка поиска"
            page.update()
            return

        items = resp.json()
        if not items:
            search_status.value = "Ничего не найдено"
        else:
            # Получаем url→id уже добавленных товаров
            fav_url_to_id: dict = {}
            fav_resp = api("GET", "/favorites", token=token_ref["value"])
            if fav_resp and fav_resp.status_code == 200:
                for fav in (fav_resp.json() or []):
                    fav_url_to_id[fav.get("url", "")] = fav.get("id")

            search_status.value = f"Найдено: {len(items)} товаров"
            for item in items:
                item_url = item.get("url", "")
                existing_id = fav_url_to_id.get(item_url)
                already = existing_id is not None
                results_grid.controls.append(
                    product_card(item, add_to_favorites, remove_from_search_fav, page,
                                 already_added=already, fav_id=existing_id)
                )
        page.update()

    def add_to_favorites(item: dict):
        resp = api("POST", "/favorites", token=token_ref["value"], json=item)
        if resp is None:
            show_snack("Нет связи с сервером", error=True)
            return False
        elif resp.status_code == 201:
            show_snack(f"«{item['title'][:28]}…» добавлен")
            return safe_json(resp)   # возвращаем dict с id
        elif resp.status_code == 409:
            show_snack("Уже в вашем списке")
            return True   # заблокируем кнопку, но id не знаем
        else:
            show_snack("Не удалось добавить", error=True)
            return False

    def remove_from_search_fav(product_id_or_url, lookup: bool = False):
        """Callback для кнопки «В избранном ✓» в карточке поиска.
        lookup=True: вернуть id по URL (когда id не знали при загрузке).
        """
        if lookup:
            fav_resp = api("GET", "/favorites", token=token_ref["value"])
            if fav_resp and fav_resp.status_code == 200:
                for fav in (fav_resp.json() or []):
                    if fav.get("url") == product_id_or_url:
                        return fav.get("id")
            return None
        resp = api("DELETE", f"/favorites/{product_id_or_url}", token=token_ref["value"])
        if resp and resp.status_code == 204:
            show_snack("Удалено из избранного")
        else:
            show_snack("Не удалось удалить", error=True)

    search_field.on_submit = do_search

    home_page = ft.View(
        route="/home",
        bgcolor=BG_COLOR,
        padding=ft.padding.all(0),
        controls=[
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    # ── Шапка ──
                    ft.Container(
                        bgcolor=SURFACE_COLOR,
                        border=ft.border.only(bottom=ft.BorderSide(1, BORDER_COLOR)),
                        padding=ft.padding.symmetric(horizontal=28, vertical=16),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        ft.Icon(ft.icons.SEARCH, color=ACCENT, size=26),
                                        ft.Text("Скидочный сыщик", color=TEXT_PRIMARY,
                                                size=20, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.TextButton(
                                            "Мой список",
                                            icon=ft.icons.STAR,
                                            on_click=lambda e: page.go("/favorites"),
                                            style=ft.ButtonStyle(color=GOLD),
                                        ),
                                        ft.TextButton(
                                            "Выйти",
                                            icon=ft.icons.LOGOUT,
                                            on_click=lambda e: logout(),
                                            style=ft.ButtonStyle(color=TEXT_SECONDARY),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    # ── Поиск ──
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=28, vertical=20),
                        content=ft.Row(
                            spacing=12,
                            controls=[
                                search_field,
                                make_button("Найти", do_search),
                                loading_ring,
                            ],
                        ),
                    ),
                    ft.Container(
                        padding=ft.padding.only(left=28, bottom=10),
                        content=search_status,
                    ),
                    # ── Сетка результатов ──
                    ft.Container(
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=28),
                        content=results_grid,
                    ),
                ],
            ),
        ],
    )

    # ════════════════════════════════════════════
    #  СТРАНИЦА 3: МОЙ СПИСОК (избранное)
    # ════════════════════════════════════════════

    fav_list      = ft.ListView(expand=True, spacing=12, padding=ft.padding.all(28))
    fav_status    = ft.Text("", color=TEXT_SECONDARY, size=14)
    fav_loading   = ft.ProgressRing(color=ACCENT, visible=False)

    def load_favorites():
        fav_loading.visible = True
        fav_list.controls.clear()
        fav_status.value = ""
        page.update()

        resp = api("GET", "/favorites", token=token_ref["value"])
        fav_loading.visible = False

        if resp is None:
            fav_status.value = "Нет связи с сервером"
            page.update()
            return
        if resp.status_code == 401:
            page.go("/")
            return

        items = resp.json()
        if not items:
            fav_status.value = "Список пуст. Найдите товары и добавьте их!"
        else:
            fav_status.value = f"Товаров в списке: {len(items)}"
            for item in items:
                fav_list.controls.append(favorite_card(item, remove_favorite, page))
        page.update()

    def remove_favorite(item: dict):
        resp = api("DELETE", f"/favorites/{item['id']}", token=token_ref["value"])
        if resp and resp.status_code == 204:
            show_snack("Товар удалён")
            load_favorites()
        else:
            show_snack("Не удалось удалить", error=True)

    favorites_page = ft.View(
        route="/favorites",
        bgcolor=BG_COLOR,
        padding=ft.padding.all(0),
        controls=[
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    # ── Шапка ──
                    ft.Container(
                        bgcolor=SURFACE_COLOR,
                        border=ft.border.only(bottom=ft.BorderSide(1, BORDER_COLOR)),
                        padding=ft.padding.symmetric(horizontal=28, vertical=16),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        ft.Icon(ft.icons.STAR, color=GOLD, size=26),
                                        ft.Text("Мой список", color=TEXT_PRIMARY,
                                                size=20, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.TextButton(
                                            "Поиск",
                                            icon=ft.icons.SEARCH,
                                            on_click=lambda e: page.go("/home"),
                                            style=ft.ButtonStyle(color=ACCENT_LIGHT),
                                        ),
                                        ft.TextButton(
                                            "Обновить",
                                            icon=ft.icons.REFRESH,
                                            on_click=lambda e: load_favorites(),
                                            style=ft.ButtonStyle(color=TEXT_SECONDARY),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        padding=ft.padding.only(left=28, top=16, bottom=4),
                        content=ft.Row(spacing=12, controls=[fav_status, fav_loading]),
                    ),
                    ft.Container(expand=True, content=fav_list),
                ],
            ),
        ],
    )

    # ════════════════════════════════════════════
    #  Роутинг
    # ════════════════════════════════════════════

    def route_change(e: ft.RouteChangeEvent):
        page.views.clear()
        if page.route == "/home":
            page.views.append(home_page)
        elif page.route == "/favorites":
            page.views.append(favorites_page)
            # Загружаем избранное при переходе на страницу
            threading.Thread(target=load_favorites, daemon=True).start()
        else:
            page.views.append(auth_page)
        page.update()

    def view_pop(e: ft.ViewPopEvent):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    def logout():
        token_ref["value"] = None
        results_grid.controls.clear()
        search_field.value = ""
        page.go("/")

    page.on_route_change = route_change
    page.on_view_pop     = view_pop
    page.go("/")


if __name__ == "__main__":
    ft.app(target=main)
