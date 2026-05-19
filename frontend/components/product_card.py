import flet as ft
from core.constants import (
    SURFACE_COLOR, BORDER_COLOR, ACCENT, GREEN, TEXT_PRIMARY, TEXT_SECONDARY, GOLD
)
from core.utils import discount_pct
from components.common import star_row

def product_card(item: dict, on_favorite, on_cancel, page: ft.Page,
                 already_added: bool = False, fav_id: int = None) -> ft.Container:
    pct = discount_pct(item["current_price"], item.get("old_price", 0))
    has_discount = pct > 0
    marketplace_colors = {"WB": "#CB11AB", "Ozon": "#005BFF", "Ya": "#FFCC00"}
    mp_color = marketplace_colors.get(item.get("marketplace_name", "WB"), ACCENT)
    
    rating_widget = star_row(item["rating"], 0) if item.get("rating") else None

    saved_id: dict = {"value": fav_id}
    is_added: dict = {"value": already_added}


    fav_btn = ft.ElevatedButton(
        text="В избранном ✓" if already_added else "В избранное",
        icon=ft.icons.STAR if already_added else ft.icons.STAR_OUTLINE,
        expand=True,
        style=ft.ButtonStyle(
            bgcolor="#1F22C55E" if already_added else "#1FF59E0B",
            color=GREEN if already_added else GOLD,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
    )

    def handle_fav(e):
        e.stop_propagation = True
        if is_added["value"]:
            if on_cancel:
                fav_item_id = saved_id["value"]
                if not fav_item_id:
                    fav_item_id = on_cancel(item["url"], lookup=True)
                if fav_item_id:
                    on_cancel(fav_item_id)
            fav_btn.text = "В избранное"
            fav_btn.icon = ft.icons.STAR_OUTLINE
            fav_btn.style.bgcolor = "#1FF59E0B"
            fav_btn.style.color = GOLD
            saved_id["value"] = None
            is_added["value"] = False
        else:
            result = on_favorite(item)
            if result:
                fav_btn.text = "В избранном ✓"
                fav_btn.icon = ft.icons.STAR
                fav_btn.style.bgcolor = "#1F22C55E"
                fav_btn.style.color = GREEN
                if isinstance(result, dict):
                    saved_id["value"] = result.get("id")
                is_added["value"] = True
        page.update()

    fav_btn.on_click = handle_fav

    card_content = ft.Column(
        spacing=12,
        expand=True,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Column(
                spacing=8,
                controls=[
                    ft.Text(item["title"], size=14, weight=ft.FontWeight.W_500,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, color=TEXT_PRIMARY),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.START,
                        spacing=8,
                        controls=[
                            ft.Text(f"₽ {item['current_price']:,.0f}".replace(",", " "),
                                    size=18, weight=ft.FontWeight.BOLD, color=GREEN),
                            ft.Text(f"₽ {item['old_price']:,.0f}".replace(",", " "),
                                    size=13, color=TEXT_SECONDARY,
                                    visible=has_discount,
                                    style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH)) if has_discount else ft.Container(),
                        ],
                    ),
                    rating_widget if rating_widget else ft.Container(),
                ],
            ),
            ft.Row(controls=[fav_btn]),
        ],
    )

    card_inner = ft.Column(
        spacing=0, tight=True,
        expand=True,
        controls=[

            ft.Container(
                height=280,
                content=ft.Stack(
                    controls=[
                        ft.Image(
                            src=item.get("image_url") or "https://via.placeholder.com/300x145",
                            width=310, height=280,
                            fit=ft.ImageFit.COVER,
                        ),
                        ft.Container(
                            content=ft.Text(item.get("marketplace_name", ""),
                                            color="white", size=10, weight=ft.FontWeight.BOLD),
                            bgcolor=mp_color,
                            border_radius=ft.border_radius.only(bottom_right=7),
                            padding=ft.padding.symmetric(horizontal=7, vertical=3),
                            top=0, left=0,
                        ),
                    ],
                ),
            ),

            ft.Container(
                padding=ft.padding.all(14),
                expand=True,
                content=card_content,
            ),
        ],
    )

    return ft.Container(
        width=310,
        height=500,
        bgcolor=SURFACE_COLOR,
        border_radius=12,
        border=ft.border.all(1, BORDER_COLOR),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=card_inner,
        on_click=lambda _: page.launch_url(item["url"]),
    )
