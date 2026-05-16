import flet as ft
from core.constants import BG_COLOR, SURFACE_COLOR, BORDER_COLOR, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, GOLD, ACCENT_LIGHT
from core.api import api, safe_json
from core.utils import normalize_url
from components.common import make_button
from components.product_card import product_card

def get_home_view(page: ft.Page, token_ref: dict, show_snack, logout_fn):
    search_field = ft.TextField(
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
    results_grid = ft.GridView(
        expand=True,
        max_extent=300,
        spacing=16,
        run_spacing=16,
        child_aspect_ratio=0.6,
    )
    search_status = ft.Text("", color=TEXT_SECONDARY, size=14)
    loading_ring  = ft.ProgressRing(color=ACCENT, visible=False)

    def add_to_favorites(item: dict):
        resp = api("POST", "/favorites", token=token_ref["value"], json=item)
        if resp is None:
            show_snack("Нет связи с сервером", error=True)
            return False
        elif resp.status_code == 201:
            show_snack(f"«{item['title'][:28]}…» добавлен")
            return safe_json(resp)
        elif resp.status_code == 409:
            show_snack("Уже в вашем списке")
            return True
        else:
            show_snack("Не удалось добавить", error=True)
            return False

    def remove_from_search_fav(product_id_or_url, lookup: bool = False):
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
            fav_url_to_id: dict = {}
            fav_resp = api("GET", "/favorites", token=token_ref["value"])
            if fav_resp and fav_resp.status_code == 200:
                for fav in (fav_resp.json() or []):
                    norm_fav_url = normalize_url(fav.get("url", ""))
                    fav_url_to_id[norm_fav_url] = fav.get("id")

            search_status.value = f"Найдено: {len(items)} товаров"
            for item in items:
                item_url = item.get("url", "")
                existing_id = fav_url_to_id.get(normalize_url(item_url))
                already = existing_id is not None
                results_grid.controls.append(
                    product_card(item, add_to_favorites, remove_from_search_fav, page,
                                 already_added=already, fav_id=existing_id)
                )
        page.update()

    search_field.on_submit = do_search

    def clear_data():
        search_field.value = ""
        results_grid.controls.clear()
        search_status.value = ""
        page.update()

    view = ft.View(
        route="/home",
        bgcolor=BG_COLOR,
        padding=ft.padding.all(0),
        controls=[
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
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
                                            on_click=lambda e: logout_fn(),
                                            style=ft.ButtonStyle(color=TEXT_SECONDARY),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ),
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
                    ft.Container(
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=28),
                        content=results_grid,
                    ),
                ],
            ),
        ],
    )
    view.clear_data = clear_data
    return view
