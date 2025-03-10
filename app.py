import streamlit as st
import pandas as pd
import re
import asyncio
import nest_asyncio
import os
import tempfile
import zipfile
import io
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Apply nest_asyncio to allow nested event loops.
nest_asyncio.apply()

# -------------------------------------------
# Translation Dictionary
# -------------------------------------------
MESSAGES = {
    "title": {"en": "Telegram Post Data Retriever", "uk": "Отримувач даних публікацій Telegram"},
    "description": {
        "en": "This app retrieves data from Telegram posts using your Telethon API credentials.",
        "uk": "Цей додаток отримує дані з публікацій Telegram, використовуючи ваші облікові дані Telethon API."
    },
    "overview": {
        "en": (
            "### Overview:\n\n"
            "1. Retrieve your Telegram API credentials by visiting [my.telegram.org](https://my.telegram.org). Log in with your phone number, then navigate to **API Development Tools** to create a new application. Your API ID and API Hash will be provided.\n\n"
            "2. Enter your API credentials and phone number below, then click **Sign In**.\n\n"
            "3. If required, enter the authentication code that Telegram sends you. If two‐factor authentication is enabled, you will then be prompted for your password.\n\n"
            "4. Once signed in, enter one or more Telegram post or chat links (e.g. `https://t.me/channel/12345` or `https://t.me/c/1567469683/2394725`) to retrieve message data. The data will be displayed in a table and as raw message objects.\n\n"
            "   **Note on Raw Message Objects:** These contain the full JSON data from Telegram, which is critical in a judicial setting as it preserves all metadata, timestamps, and any hidden attributes of the messages. This raw data can be used as evidence to validate the authenticity and context of the posts.\n\n"
            "5. If any posts contain media (including files in galleries), a button will appear allowing you to download all media in a ZIP archive.\n\n"
            "If you encounter a **'database is locked'** error, click **Reset Session** to disconnect any previous session."
        ),
        "uk": (
            "### Огляд:\n\n"
            "1. Отримайте свої облікові дані Telegram API, відвідавши [my.telegram.org](https://my.telegram.org). Увійдіть за допомогою свого номера телефону, а потім перейдіть до **API Development Tools**, щоб створити новий додаток. Вам будуть надані API ID та API Hash.\n\n"
            "2. Введіть свої облікові дані API та номер телефону нижче, а потім натисніть **Увійти**.\n\n"
            "3. Якщо потрібно, введіть код аутентифікації, який надсилає Telegram. Якщо увімкнено двофакторну аутентифікацію, ви будете запитані про ваш пароль.\n\n"
            "4. Після входу введіть одне або декілька посилань публікацій або чатів Telegram (наприклад, `https://t.me/channel/12345` або `https://t.me/c/1567469683/2394725`), щоб отримати дані повідомлень. Дані будуть відображені у вигляді таблиці та як сирі об'єкти повідомлень.\n\n"
            "   **Примітка про сирі об'єкти повідомлень:** Вони містять повні JSON-дані з Telegram, що є критично важливим у судовому процесі, оскільки зберігають всю метадані, часові мітки та інші приховані атрибути повідомлень. Ці сирі дані можна використати як докази для підтвердження автентичності та контексту публікацій.\n\n"
            "5. Якщо будь-яка публікація містить медіа (у тому числі файли з галереї), з'явиться кнопка, яка дозволить завантажити всі медіа у вигляді ZIP-архіву.\n\n"
            "Якщо ви отримаєте помилку **'database is locked'**, натисніть **Скинути сесію**, щоб розірвати попередню сесію."
        )
    },
    "reset_session": {"en": "Reset Session", "uk": "Скинути сесію"},
    "reset_success": {"en": "Session reset successfully.", "uk": "Сесію скинуто успішно."},
    "step1": {"en": "Step 1: Sign in to Telegram", "uk": "Крок 1: Увійдіть у Telegram"},
    "enter_api_id": {"en": "Enter your API ID", "uk": "Введіть ваш API ID"},
    "enter_api_hash": {"en": "Enter your API Hash", "uk": "Введіть ваш API Hash"},
    "enter_phone": {
        "en": "Enter your phone number (with country code, e.g. +441234567890)",
        "uk": "Введіть свій номер телефону (з кодом країни, наприклад, +441234567890)"
    },
    "sign_in": {"en": "Sign In", "uk": "Увійти"},
    "credentials_missing": {
        "en": "Please provide all credentials (API ID, API Hash and phone number).",
        "uk": "Будь ласка, надайте всі облікові дані (API ID, API Hash та номер телефону)."
    },
    "api_id_int_error": {"en": "API ID must be an integer.", "uk": "API ID має бути цілим числом."},
    "signing_in_spinner": {"en": "Signing in to Telegram...", "uk": "Вхід у Telegram..."},
    "sign_in_success": {"en": "Signed in successfully!", "uk": "Вхід успішний!"},
    "sign_in_error_prefix": {"en": "An error occurred during sign in: ", "uk": "Сталася помилка при вході: "},
    "awaiting_code_msg": {
        "en": "An authentication code has been sent. Please enter it below and click 'Submit Code'.",
        "uk": "Код аутентифікації надіслано. Будь ласка, введіть його нижче та натисніть 'Відправити код'."
    },
    "enter_auth_code": {"en": "Enter authentication code", "uk": "Введіть код аутентифікації"},
    "submit_code": {"en": "Submit Code", "uk": "Відправити код"},
    "signing_in_with_code_spinner": {"en": "Signing in...", "uk": "Вхід..."},
    "enter_password": {"en": "Enter your 2FA password", "uk": "Введіть ваш 2FA пароль"},
    "submit_password": {"en": "Submit Password", "uk": "Відправити пароль"},
    "2fa_required": {
        "en": "Two-factor authentication is enabled. Please enter your password.",
        "uk": "Увімкнено двофакторну аутентифікацію. Будь ласка, введіть свій пароль."
    },
    "step2": {"en": "Step 2: Enter Telegram Post Links", "uk": "Крок 2: Введіть посилання публікацій Telegram"},
    "enter_links": {
        "en": "Enter one or more Telegram post links (separated by spaces, commas, or new lines)",
        "uk": "Введіть одне або декілька посилань публікацій Telegram (розділених пробілами, комами або новими рядками)"
    },
    "processed_links": {"en": "Processed Links:", "uk": "Оброблені посилання:"},
    "retrieving_data_spinner": {"en": "Retrieving message data...", "uk": "Отримання даних повідомлення..."},
    "retrieved_data": {"en": "Retrieved Telegram Data", "uk": "Отримані дані Telegram"},
    "download_csv": {"en": "Download data as CSV", "uk": "Завантажити дані у форматі CSV"},
    "raw_message_objects": {"en": "Raw Message Objects", "uk": "Сирі об'єкти повідомлень"},
    "message_object": {"en": "Message Object", "uk": "Об'єкт повідомлення"},
    "no_links_error": {"en": "Please enter some Telegram post links.", "uk": "Будь ласка, введіть посилання публікацій Telegram."},
    "no_message_data_warning": {
        "en": "No message data was retrieved. Please check your links or try again.",
        "uk": "Дані повідомлень не отримано. Будь ласка, перевірте посилання або спробуйте знову."
    },
    "link_not_recognised": {"en": "Link not recognised:", "uk": "Посилання не розпізнано:"},
    "processing_message": {
        "en": "Processing message from **{channel}** with ID **{msg_id}**",
        "uk": "Обробка повідомлення з **{channel}** з ID **{msg_id}**"
    },
    "no_message_found": {
        "en": "No message found for link: {link}",
        "uk": "Не знайдено повідомлення для посилання: {link}"
    },
    "download_all_media": {"en": "Download All Media", "uk": "Завантажити всі медіа"},
    "downloading_media_spinner": {"en": "Downloading media...", "uk": "Завантаження медіа..."}
}

# -------------------------------------------
# Language Selection
# -------------------------------------------
language = st.selectbox("Select Language", options=["English", "Українська"])
lang = "en" if language == "English" else "uk"

# -------------------------------------------
# Overview Section
# -------------------------------------------
st.markdown(MESSAGES["overview"][lang])

# -------------------------------------------
# Asynchronous functions for Telegram operations
# -------------------------------------------
async def async_get_telegram_client(api_id, api_hash, phone):
    # Use a session file name that includes the phone number.
    client = TelegramClient("session_" + phone, api_id, api_hash)
    await client.connect()  # Connect without interactive prompts.
    return client

# -------------------------------------------
# Helper function to process links (handles both username and /c/ chat links)
# -------------------------------------------
def process_link(link):
    # If the link is in the /c/ format (for chats)
    pattern_chat = r"(?:https?://)?t\.me/c/(\d+)/(\d+)"
    match_chat = re.search(pattern_chat, link)
    if match_chat:
        # For t.me/c/ links, the channel identifier is calculated as follows:
        # Actual channel id = -(int(part) + 1000000000000)
        channel_id = -(int(match_chat.group(1)) + 1000000000000)
        message_id = int(match_chat.group(2))
        return channel_id, message_id
    # Otherwise, try the standard pattern with username.
    pattern_username = r"(?:https?://)?t\.me/([^/]+)/(\d+)"
    match_username = re.search(pattern_username, link)
    if match_username:
        username = match_username.group(1)
        message_id = int(match_username.group(2))
        return username, message_id
    return None, None

async def get_message_data(client, channel_identifier, message_id):
    try:
        message = await client.get_messages(channel_identifier, ids=message_id)
    except Exception as e:
        return None, str(e)
    return message, None

async def process_messages(client, links):
    results = []
    raw_messages = []
    for link in links:
        channel_identifier, message_id = process_link(link)
        if channel_identifier is None:
            st.warning(f"{MESSAGES['link_not_recognised'][lang]} {link}")
            continue
        display_channel = channel_identifier if isinstance(channel_identifier, str) else f"Chat {channel_identifier}"
        st.write(MESSAGES["processing_message"][lang].format(channel=display_channel, msg_id=message_id))
        message, error = await get_message_data(client, channel_identifier, message_id)
        if error:
            st.error(MESSAGES["sign_in_error_prefix"][lang] + f"{link}: {error}")
            continue
        if message:
            raw_messages.append((link, message))
            reactions_str = ""
            if message.reactions and hasattr(message.reactions, 'results') and message.reactions.results:
                reactions_list = [
                    f"{reaction.reaction.emoticon}: {reaction.count}"
                    for reaction in message.reactions.results
                    if reaction.reaction and hasattr(reaction.reaction, 'emoticon')
                ]
                reactions_str = ", ".join(reactions_list)
            entities_str = ""
            if message.entities:
                entities_str = ", ".join({type(entity).__name__ for entity in message.entities})
            data = {
                "Channel": display_channel,
                "Message ID": message.id,
                "Date": message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else None,
                "Edit Date": message.edit_date.strftime("%Y-%m-%d %H:%M:%S") if message.edit_date else None,
                "Text": message.message,
                "Media Present": "Yes" if message.media else "No",
                "Media Type": type(message.media).__name__ if message.media else None,
                "Views": message.views,
                "Forwards": message.forwards,
                "Reactions": reactions_str,
                "Entities": entities_str,
                "Pinned": message.pinned,
                "Silent": message.silent,
                "Post": message.post,
                "Forwarded": "Yes" if message.fwd_from else "No",
                "Via Bot": message.via_bot_id,
                "Grouped ID": message.grouped_id,
            }
            results.append(data)
        else:
            st.warning(MESSAGES["no_message_found"][lang].format(link=link))
    return results, raw_messages

# -------------------------------------------
# Async function to download all media from raw messages.
# -------------------------------------------
async def download_all_media(client, raw_messages):
    media_files = []
    # Create a temporary directory to download media
    with tempfile.TemporaryDirectory() as tmpdirname:
        for link, message in raw_messages:
            if message.media:
                # Download the media file into the temporary directory.
                file_path = await client.download_media(message.media, file=tmpdirname)
                if file_path:
                    media_files.append(file_path)
        # Create a zip archive of all downloaded media
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for file_path in media_files:
                zipf.write(file_path, arcname=os.path.basename(file_path))
        zip_buffer.seek(0)
        return zip_buffer.read()

# -------------------------------------------
# Session Management and Reset
# -------------------------------------------
if "loop" not in st.session_state:
    st.session_state.loop = asyncio.new_event_loop()

if st.button(MESSAGES["reset_session"][lang]):
    if "client" in st.session_state:
        st.session_state.loop.run_until_complete(st.session_state.client.disconnect())
        del st.session_state.client
    session_file = None
    for f in os.listdir("."):
        if f.startswith("session_") and f.endswith(".session"):
            session_file = f
            break
    if session_file:
        os.remove(session_file)
    st.success(MESSAGES["reset_success"][lang])

# -------------------------------------------
# Streamlit UI - Sign In
# -------------------------------------------
st.header(MESSAGES["step1"][lang])
api_id_input = st.text_input(MESSAGES["enter_api_id"][lang])
api_hash_input = st.text_input(MESSAGES["enter_api_hash"][lang])
phone_input = st.text_input(MESSAGES["enter_phone"][lang])

if st.button(MESSAGES["sign_in"][lang]):
    if not api_id_input or not api_hash_input or not phone_input:
        st.error(MESSAGES["credentials_missing"][lang])
    else:
        try:
            api_id_int = int(api_id_input)
        except ValueError:
            st.error(MESSAGES["api_id_int_error"][lang])
        else:
            with st.spinner(MESSAGES["signing_in_spinner"][lang]):
                try:
                    client = st.session_state.loop.run_until_complete(
                        async_get_telegram_client(api_id_int, api_hash_input, phone_input)
                    )
                    st.session_state.client = client
                    st.session_state.phone = phone_input
                    if not st.session_state.loop.run_until_complete(client.is_user_authorized()):
                        st.session_state.loop.run_until_complete(client.send_code_request(phone_input))
                        st.session_state.awaiting_code = True
                        st.info(MESSAGES["awaiting_code_msg"][lang])
                    else:
                        st.success(MESSAGES["sign_in_success"][lang])
                except Exception as e:
                    st.error(MESSAGES["sign_in_error_prefix"][lang] + str(e))

# -------------------------------------------
# Two-Step Authentication: Enter Code if Needed
# -------------------------------------------
if st.session_state.get("awaiting_code", False):
    auth_code = st.text_input(MESSAGES["enter_auth_code"][lang], key="auth_code")
    if st.button(MESSAGES["submit_code"][lang]):
        with st.spinner(MESSAGES["signing_in_with_code_spinner"][lang]):
            try:
                st.session_state.loop.run_until_complete(
                    st.session_state.client.sign_in(phone_input, auth_code)
                )
                st.success(MESSAGES["sign_in_success"][lang])
                st.session_state.awaiting_code = False
            except SessionPasswordNeededError:
                st.info(MESSAGES["2fa_required"][lang])
                st.session_state.awaiting_code = False
                st.session_state.awaiting_password = True
            except Exception as e:
                st.error(MESSAGES["auth_sign_in_error_prefix"][lang] + str(e))

# -------------------------------------------
# Two-Step Authentication: Enter Password if 2FA is Required
# -------------------------------------------
if st.session_state.get("awaiting_password", False):
    password = st.text_input(MESSAGES["enter_password"][lang], type="password", key="password")
    if st.button(MESSAGES["submit_password"][lang]):
        with st.spinner(MESSAGES["signing_in_with_code_spinner"][lang]):
            try:
                st.session_state.loop.run_until_complete(
                    st.session_state.client.sign_in(password=password)
                )
                st.success(MESSAGES["sign_in_success"][lang])
                st.session_state.awaiting_password = False
            except Exception as e:
                st.error(MESSAGES["auth_sign_in_error_prefix"][lang] + str(e))

# -------------------------------------------
# Streamlit UI - Process Links
# -------------------------------------------
if "client" in st.session_state and not st.session_state.get("awaiting_code", False) and not st.session_state.get("awaiting_password", False):
    st.header(MESSAGES["step2"][lang])
    links_input = st.text_area(MESSAGES["enter_links"][lang])
    if st.button(MESSAGES["sign_in"][lang] + " & " + MESSAGES["step2"][lang]):
        if links_input:
            links = [link.strip() for link in re.split(r"[\s,]+", links_input) if link.strip()]
            st.write(MESSAGES["processed_links"][lang], ", ".join(links))
            with st.spinner(MESSAGES["retrieving_data_spinner"][lang]):
                results, raw_messages = st.session_state.loop.run_until_complete(
                    process_messages(st.session_state.client, links)
                )
            if results:
                df = pd.DataFrame(results)
                st.subheader(MESSAGES["retrieved_data"][lang])
                st.dataframe(df)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=MESSAGES["download_csv"][lang],
                    data=csv,
                    file_name="telegram_messages.csv",
                    mime="text/csv"
                )
            else:
                st.warning(MESSAGES["no_message_data_warning"][lang])
            if raw_messages:
                st.subheader(MESSAGES["raw_message_objects"][lang])
                for link, message in raw_messages:
                    with st.expander(f"Message from {link}"):
                        st.text_area(MESSAGES["message_object"][lang], value=str(message), height=200, disabled=True)
            # Check if any raw message has media
            if any(message.media for _, message in raw_messages):
                if st.button(MESSAGES["download_all_media"][lang]):
                    with st.spinner(MESSAGES["downloading_media_spinner"][lang]):
                        zip_bytes = st.session_state.loop.run_until_complete(
                            download_all_media(st.session_state.client, raw_messages)
                        )
                    st.download_button(
                        label=MESSAGES["download_all_media"][lang],
                        data=zip_bytes,
                        file_name="media.zip",
                        mime="application/zip"
                    )
        else:
            st.error(MESSAGES["no_links_error"][lang])
