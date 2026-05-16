import flet as ft
from core.constants import BG_COLOR, SURFACE_COLOR, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, GOLD, ACCENT_LIGHT, ACCENT
from core.api import api
from components.favorite_card import favorite_card

def get_favorites_view(page: ft.Page, token_ref: dict, show_snack):
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

    view = ft.View(
        route="/favorites",
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
    
    # Store load_favorites on the view object so app.py can trigger it
    view.load_data = load_favorites
    return view
