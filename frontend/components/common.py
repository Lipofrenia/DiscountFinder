import flet as ft
from core.constants import BORDER_COLOR, ACCENT, SURFACE_COLOR, TEXT_SECONDARY, TEXT_PRIMARY, GOLD

def make_text_field(label: str, password: bool = False, ref=None) -> ft.TextField:
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
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ACCENT if primary else SURFACE_COLOR,
            color=TEXT_PRIMARY,
            overlay_color="#267C3AED",
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=ft.padding.symmetric(horizontal=24, vertical=14),
        ),
    )


def star_row(rating: float, reviews: int) -> ft.Row:
    stars = []
    for i in range(1, 6):
        color = GOLD if rating >= (i - 0.25) else ("#88F59E0B" if rating >= (i - 0.75) else BORDER_COLOR)
        stars.append(ft.Icon(ft.icons.STAR, color=color, size=13))
    return ft.Row(
        spacing=2,
        controls=[
            *stars,
            ft.Text(f"{rating:.1f}", color=TEXT_SECONDARY, size=11),
        ],
    )
