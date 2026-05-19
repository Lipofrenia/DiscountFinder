import flet as ft
import re
from core.constants import BG_COLOR, SURFACE_COLOR, BORDER_COLOR, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, RED, GREEN, ACCENT_LIGHT
from core.api import api, safe_json
from components.common import make_text_field, make_button

def get_auth_view(page: ft.Page, token_ref: dict):
    email_field    = make_text_field("Email")
    password_field = make_text_field("Пароль", password=True)
    auth_error     = ft.Text("", color=RED, size=13)
    auth_mode      = {"reg": False}

    def validate_form(email: str, pwd: str) -> str | None:
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
            toggle_mode_text.text = "Уже есть аккаунт? Войти"
        else:
            auth_btn.text = "Войти"
            toggle_mode_text.text = "Нет аккаунта? Зарегистрироваться"
        auth_error.value = ""
        page.update()

    toggle_mode_text = ft.TextButton(
        "Нет аккаунта? Зарегистрироваться",
        on_click=toggle_mode,
        style=ft.ButtonStyle(color=ACCENT_LIGHT),
    )

    return ft.View(
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
                    color="#667C3AED",
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
