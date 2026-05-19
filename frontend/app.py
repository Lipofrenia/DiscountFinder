

import flet as ft
import threading
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.constants import BG_COLOR, SURFACE_COLOR, RED, GREEN
from views.auth import get_auth_view
from views.home import get_home_view
from views.favorites import get_favorites_view

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


    token_ref = {"value": None}
    snack_ref = ft.SnackBar(content=ft.Text(""), bgcolor=SURFACE_COLOR)
    page.overlay.append(snack_ref)

    def show_snack(msg: str, error: bool = False):
        snack_ref.content = ft.Text(msg, color=RED if error else GREEN)
        snack_ref.bgcolor = SURFACE_COLOR
        snack_ref.open = True
        page.update()

    def logout():
        token_ref["value"] = None
        if hasattr(home_view, "clear_data"):
            home_view.clear_data()
        page.go("/")


    auth_view = get_auth_view(page, token_ref)
    home_view = get_home_view(page, token_ref, show_snack, logout)
    fav_view = get_favorites_view(page, token_ref, show_snack)

    def route_change(e: ft.RouteChangeEvent):
        page.views.clear()
        
        if page.route == "/home":
            page.views.append(home_view)
        elif page.route == "/favorites":
            fav_view = get_favorites_view(page, token_ref, show_snack)
            page.views.append(fav_view)
            if hasattr(fav_view, "load_data"):
                threading.Thread(target=fav_view.load_data, daemon=True).start()
        else:
            page.views.append(auth_view)
            
        page.update()

    def view_pop(e: ft.ViewPopEvent):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop     = view_pop
    page.go("/")


if __name__ == "__main__":
    ft.app(target=main)
