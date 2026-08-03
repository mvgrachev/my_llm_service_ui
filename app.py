#!/usr/bin/env python3
"""Streamlit UI for LLM Service."""

import os

import streamlit as st
import requests

# Page config
st.set_page_config(
    page_title="Рецепты и продукты",
    page_icon="🍳",
    layout="centered",
)

# Backend API URL — используется переменная окружения для Docker, иначе localhost
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")
API_URL = f"{FASTAPI_URL}/chat"

st.title("🍳 Подбор продуктов и рецептов")
st.markdown("Укажите блюдо, и сервис подскажет нужные продукты и шаги приготовления.")

# Form inputs
with st.form("chat_form"):
    dish = st.text_input("Блюдо:", placeholder="Например: борщ")

    col1, col2 = st.columns(2)
    with col1:
        people = st.number_input(
            "Количество персон:",
            min_value=1,
            max_value=1000,
            value=2,
        )
    with col2:
        use_steps = st.checkbox("Показать шаги приготовления", value=True)

    submitted = st.form_submit_button("Отправить", type="primary", use_container_width=True)

if submitted:
    if not dish.strip():
        st.warning("⚠️ Пожалуйста, введите название блюда.")
    else:
        with st.spinner("⏳ Обработка запроса..."):
            while True:
                try:
                    response = requests.post(
                        API_URL,
                        json={
                            "dish": dish.strip(),
                            "people": people,
                            "use_steps": use_steps,
                        },
                        timeout=60,
                    )
                    data = response.json()

                    # AuthError — поле "message"
                    if "message" in data:
                        st.error(f"🔑 {data['message']}")
                        break

                    # Ошибки авторизации по HTTP-коду 401
                    if response.status_code == 401:
                        st.error("🔑 Ошибка авторизации: недействительный или истёкший API-ключ. Пожалуйста, проверьте настройки.")
                        break

                    response.raise_for_status()

                    st.success("✅ Запрос выполнен успешно!")

                    st.markdown("### 🛒 Продукты")
                    products = data.get("products", [])
                    if products:
                        for i, product in enumerate(products, 1):
                            st.markdown(f"{i}. {product}")
                    else:
                        st.info("Продукты не найдены.")

                    steps = data.get("steps")
                    if steps and use_steps:
                        st.markdown("### 📝 Шаги приготовления")
                        for i, step in enumerate(steps, 1):
                            st.markdown(f"**Шаг {i}:** {step}")

                    break

                except requests.exceptions.ConnectionError:
                    st.error("❌ Не удалось подключиться к серверу. Убедитесь, что FastAPI запущен на порту 8000.")
                    break
                except requests.exceptions.Timeout:
                    st.error("❌ Превышено время ожидания ответа от сервера.")
                    break
                except requests.exceptions.HTTPError as e:
                    st.error(f"❌ Ошибка сервера: {e}")
                    break
                except Exception as e:
                    st.error(f"❌ Произошла ошибка: {str(e)}")
                    break
