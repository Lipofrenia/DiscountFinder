import flet as ft
from core.constants import (
    SURFACE_COLOR, BORDER_COLOR, ACCENT, ACCENT_LIGHT, GREEN, RED, TEXT_PRIMARY, TEXT_SECONDARY
)
from components.common import star_row

def favorite_card(item: dict, on_delete, page: ft.Page) -> ft.Container:
    current_price = item["current_price"]
    history = item.get("price_history") or []
    expanded: dict = {"value": False}


    first_price = history[0]["price"] if history else None
    total_diff  = (current_price - first_price) if first_price and first_price != current_price else None
    total_pct   = int(total_diff / first_price * 100) if (total_diff and first_price) else None


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


    arrow_icon = ft.Icon(ft.icons.KEYBOARD_ARROW_DOWN, color=TEXT_SECONDARY, size=20)


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

    def toggle_history(e):
        expanded["value"] = not expanded["value"]
        history_panel.visible = expanded["value"]
        arrow_icon.name = (
            ft.icons.KEYBOARD_ARROW_UP if expanded["value"]
            else ft.icons.KEYBOARD_ARROW_DOWN
        )
        card_container.update()

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
    return card_container
