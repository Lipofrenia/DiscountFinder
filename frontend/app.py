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


def product_card(item: dict, on_favorite, token: str) -> ft.Container:
    """
    Карточка товара: изображение, название, цена, кнопка «В избранное».
    """
    pct = discount_pct(item["current_price"], item.get("old_price", 0))
    has_discount = pct > 0

    price_row_controls = [
        ft.Text(
            f"₽ {item['current_price']:,.0f}".replace(",", " "),
            color=GREEN if has_discount else TEXT_PRIMARY,
            size=18,
            weight=ft.FontWeight.BOLD,
        ),
    ]
    if has_discount:
        price_row_controls += [
            ft.Text(
                f"₽ {item['old_price']:,.0f}".replace(",", " "),
                color=TEXT_SECONDARY,
                size=13,
                style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH),
            ),
            ft.Container(
                content=ft.Text(f"-{pct}%", color="white", size=11, weight=ft.FontWeight.BOLD),
                bgcolor=GREEN,
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
            ),
        ]

    marketplace_colors = {"WB": "#CB11AB", "Ozon": "#005BFF", "Ya": "#FFCC00"}
    mp_color = marketplace_colors.get(item.get("marketplace_name", "WB"), ACCENT)

    return ft.Container(
        border_radius=14,
        bgcolor=SURFACE_COLOR,
        border=ft.border.all(1, BORDER_COLOR),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
        content=ft.Column(
            spacing=0,
            controls=[
                # ── Изображение ──
                ft.Stack(
                    controls=[
                        ft.Image(
                            src=item.get("image_url") or "https://via.placeholder.com/300x200",
                            width=300,
                            height=180,
                            fit=ft.ImageFit.COVER,
                            error_content=ft.Container(
                                bgcolor="#1a1a2e",
                                content=ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED, color=TEXT_SECONDARY),
                            ),
                        ),
                        # Бейдж площадки
                        ft.Container(
                            content=ft.Text(
                                item.get("marketplace_name", ""),
                                color="white",
                                size=11,
                                weight=ft.FontWeight.BOLD,
                            ),
                            bgcolor=mp_color,
                            border_radius=ft.border_radius.only(bottom_right=8),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            top=0, left=0,
                        ),
                    ],
                ),
                # ── Контент карточки ──
                ft.Container(
                    padding=ft.padding.all(14),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Text(
                                item["title"],
                                color=TEXT_PRIMARY,
                                size=13,
                                weight=ft.FontWeight.W_500,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(
                                controls=price_row_controls,
                                wrap=True,
                                spacing=8,
                                run_spacing=4,
                            ),
                            ft.ElevatedButton(
                                text="В избранное",
                                icon=ft.icons.STAR_OUTLINE,
                                on_click=lambda e, i=item: on_favorite(i),
                                style=ft.ButtonStyle(
                                    bgcolor="#1FF59E0B",  # ~12% opacity gold
                                    color=GOLD,
                                    overlay_color="#33F59E0B",  # ~20% opacity gold
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )


def favorite_card(item: dict, on_delete) -> ft.Container:
    """Карточка товара в разделе «Мой список»."""
    pct = discount_pct(item["current_price"], item.get("old_price") or 0)
    has_discount = pct > 0

    return ft.Container(
        border_radius=12,
        bgcolor=SURFACE_COLOR,
        border=ft.border.all(1, BORDER_COLOR),
        padding=ft.padding.all(16),
        content=ft.Row(
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Image(
                    src=item.get("image_url") or "https://via.placeholder.com/80",
                    width=80, height=80,
                    fit=ft.ImageFit.COVER,
                    border_radius=8,
                ),
                ft.Column(
                    expand=True,
                    spacing=4,
                    controls=[
                        ft.Text(item["title"], color=TEXT_PRIMARY, size=14,
                                weight=ft.FontWeight.W_500, max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Text(
                                    f"₽ {item['current_price']:,.0f}".replace(",", " "),
                                    color=GREEN if has_discount else TEXT_PRIMARY,
                                    size=16, weight=ft.FontWeight.BOLD,
                                ),
                                *(
                                    [ft.Container(
                                        content=ft.Text(f"-{pct}%", color="white",
                                                        size=11, weight=ft.FontWeight.BOLD),
                                        bgcolor=GREEN, border_radius=6,
                                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    )]
                                    if has_discount else []
                                ),
                            ],
                        ),
                        ft.Text(item.get("marketplace_name", ""), color=TEXT_SECONDARY, size=12),
                    ],
                ),
                ft.IconButton(
                    icon=ft.icons.DELETE_OUTLINE,
                    icon_color=RED,
                    tooltip="Удалить",
                    on_click=lambda e, i=item: on_delete(i),
                ),
            ],
        ),
    )


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
        runs_count=3,
        max_extent=310,
        spacing=16,
        run_spacing=16,
        child_aspect_ratio=0.72,
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
            search_status.value = f"Найдено: {len(items)} товаров"
            for item in items:
                results_grid.controls.append(
                    product_card(item, add_to_favorites, token_ref["value"])
                )
        page.update()

    def add_to_favorites(item: dict):
        resp = api("POST", "/favorites", token=token_ref["value"], json=item)
        if resp is None:
            show_snack("Нет связи с сервером", error=True)
        elif resp.status_code == 201:
            show_snack(f"«{item['title'][:30]}…» добавлен в избранное")
        else:
            show_snack("Не удалось добавить", error=True)

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
                fav_list.controls.append(favorite_card(item, remove_favorite))
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
