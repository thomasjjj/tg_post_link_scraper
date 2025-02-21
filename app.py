import streamlit as st
import pandas as pd
import re
import asyncio
import nest_asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Apply nest_asyncio to allow nested event loops if necessary.
nest_asyncio.apply()


# Define an asynchronous function to create and sign in to the Telegram client.
async def async_get_telegram_client(api_id, api_hash, phone):
    client = TelegramClient("session_name", api_id, api_hash)
    await client.start(phone=phone)
    return client


# Helper function to process an individual Telegram link.
def process_link(link):
    pattern = r"(?:https?://)?t\.me/([^/]+)/(\d+)"
    match = re.search(pattern, link)
    if match:
        channel_username = match.group(1)
        message_id = int(match.group(2))
        return channel_username, message_id
    else:
        return None, None


# Asynchronous function to retrieve a single message.
async def get_message_data(client, channel_username, message_id):
    try:
        message = await client.get_messages(channel_username, ids=message_id)
    except Exception as e:
        return None, str(e)
    return message, None


# Asynchronous function to process multiple links and compile data.
# This function returns a tuple: (results_for_table, raw_messages)
async def process_messages(client, links):
    results = []
    raw_messages = []
    for link in links:
        channel_username, message_id = process_link(link)
        if not channel_username:
            st.warning(f"Link not recognised: {link}")
            continue
        st.write(f"Processing message from **{channel_username}** with ID **{message_id}**")
        message, error = await get_message_data(client, channel_username, message_id)
        if error:
            st.error(f"Error retrieving message for link **{link}**: {error}")
            continue
        if message:
            raw_messages.append((link, message))
            # Process reactions if available.
            reactions_str = ""
            if message.reactions and hasattr(message.reactions, 'results') and message.reactions.results:
                reactions_list = [
                    f"{reaction.reaction.emoticon}: {reaction.count}"
                    for reaction in message.reactions.results
                    if reaction.reaction and hasattr(reaction.reaction, 'emoticon')
                ]
                reactions_str = ", ".join(reactions_list)
            # Process entities if available.
            entities_str = ""
            if message.entities:
                entities_str = ", ".join({type(entity).__name__ for entity in message.entities})
            data = {
                "Channel": channel_username,
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
            st.warning(f"No message found for link: {link}")
    return results, raw_messages


# -------------------------------------------
# Streamlit User Interface
# -------------------------------------------
st.title("Telegram Post Data Retriever")
st.markdown("This app retrieves data from Telegram posts using your Telethon API credentials.")

# Create a persistent event loop if not already in session state.
if "loop" not in st.session_state:
    st.session_state.loop = asyncio.new_event_loop()

# Step 1: Sign in to Telegram.
st.header("Step 1: Sign in to Telegram")
api_id_input = st.text_input("Enter your API ID")
api_hash_input = st.text_input("Enter your API Hash")
phone_input = st.text_input("Enter your phone number (with country code, e.g. +441234567890)")

if st.button("Sign In"):
    if not api_id_input or not api_hash_input or not phone_input:
        st.error("Please provide all credentials (API ID, API Hash and phone number).")
    else:
        try:
            api_id_int = int(api_id_input)
        except ValueError:
            st.error("API ID must be an integer.")
        else:
            with st.spinner("Signing in to Telegram..."):
                try:
                    # Use the persistent loop to sign in.
                    client = st.session_state.loop.run_until_complete(
                        async_get_telegram_client(api_id_int, api_hash_input, phone_input)
                    )
                    st.success("Signed in successfully!")
                    st.session_state.client = client
                except Exception as e:
                    st.error(f"An error occurred during sign in: {e}")

# Step 2: Enter Telegram Post Links.
if "client" in st.session_state:
    st.header("Step 2: Enter Telegram Post Links")
    links_input = st.text_area("Enter one or more Telegram post links (separated by spaces, commas, or new lines)")

    if st.button("Process Links"):
        if links_input:
            # Split the input by spaces, commas, or new lines.
            links = [link.strip() for link in re.split(r"[\s,]+", links_input) if link.strip()]
            st.write("Processed Links:", ", ".join(links))
            with st.spinner("Retrieving message data..."):
                results, raw_messages = st.session_state.loop.run_until_complete(
                    process_messages(st.session_state.client, links)
                )
            if results:
                df = pd.DataFrame(results)
                st.subheader("Retrieved Telegram Data")
                st.dataframe(df)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download data as CSV",
                    data=csv,
                    file_name="telegram_messages.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No message data was retrieved. Please check your links or try again.")

            # Display raw message objects in individual text boxes.
            if raw_messages:
                st.subheader("Raw Message Objects")
                for link, message in raw_messages:
                    with st.expander(f"Message from {link}"):
                        st.text_area("Message Object", value=str(message), height=200, disabled=True)
        else:
            st.error("Please enter some Telegram post links.")
