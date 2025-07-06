"""
Image Analysis Agent Chat App
=============================

Author: Om Prakash Jakhar  
Date: July 2025  
License: MIT  
Project: Image Analysis Agent using Google ADK + Streamlit

Description:
------------
This Streamlit app provides a chat-like UI for interacting with a custom image analysis agent
powered by Google's Agent Development Kit (ADK). Users can input a message and optionally
upload an image. The agent processes both inputs using Gemini models and responds with
a structured image summary.

Features:
---------
- Session-based chat system
- Image upload and preview
- Text + image (multimodal) input support
- Streamlit UI integration with ADK `api_server`

Architecture:
-------------
User input → Streamlit UI → ADK API (localhost:8000) → Gemini agent → Response → UI display

Run Instructions:
-----------------
1. Start ADK server: `adk api_server`
2. Run UI: `streamlit run apps/Image_Analysis_app.py`

"""

import streamlit as st
import requests
import json
import os
import uuid
import time
import base64

# -------------------
# Streamlit Page Setup
# -------------------

st.set_page_config(
    page_title="Image Agent",
    page_icon="🧠",
    layout="centered"
)

# -------------------
# Constants and Globals
# -------------------

API_BASE_URL = "http://localhost:8000"
APP_NAME = "image_agent"

# -------------------
# Initialize Session State
# -------------------

if "user_id" not in st.session_state:
    st.session_state.user_id = f"user-{uuid.uuid4()}"

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------
# Function: create_session
# -------------------

def create_session() -> bool:
    """
    Create a new ADK session using timestamped session ID.

    Returns:
        bool: True if session created successfully, False otherwise
    """
    session_id = f"session-{int(time.time())}"
    response = requests.post(
        f"{API_BASE_URL}/apps/{APP_NAME}/users/{st.session_state.user_id}/sessions/{session_id}",
        headers={"Content-Type": "application/json"},
        data=json.dumps({})
    )
    if response.status_code == 200:
        st.session_state.session_id = session_id
        st.session_state.messages = []
        return True
    else:
        st.error(f"Failed to create session: {response.text}")
        return False

# -------------------
# Function: send_message
# -------------------

def send_message(message: str, ip_file=None) -> bool:
    """
    Sends user text and (optional) image to ADK agent and processes the response.

    Args:
        message (str): The user input message
        ip_file (UploadedFile): Optional uploaded image file

    Returns:
        bool: True if message sent and processed successfully, False otherwise
    """
    if not st.session_state.session_id:
        st.error("Please create a session before sending messages.")
        return False

    image_bytes = None

    # Build payload
    payload = {
        "appName": APP_NAME,
        "userId": st.session_state.user_id,
        "sessionId": st.session_state.session_id,
        "newMessage": {
            "role": "user",
            "parts": [{"text": message}]
        },
        "streaming": False
    }

    if ip_file:
        image_bytes = ip_file.read()
        encoded_image = base64.b64encode(image_bytes).decode()
        payload["newMessage"]["parts"].append({
            "inlineData": {
                "displayName": "uploaded.jpg",
                "data": encoded_image,
                "mimeType": "image/jpeg"
            }
        })

    # Save user message in state
    st.session_state.messages.append({
        "role": "user",
        "content": message,
        "image_bytes": image_bytes
    })

    # Send to ADK
    response = requests.post(
        f"{API_BASE_URL}/run",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        st.error(f"Agent Error: {response.text}")
        return False

    events = response.json()
    assistant_message = None

    # Parse agent response
    for event in events:
        content = event.get("content", {})
        parts = content.get("parts", [])
        if content.get("role") == "model" and parts:
            if "text" in parts[0]:
                assistant_message = parts[0]["text"]

    # Add assistant message
    if assistant_message:
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_message
        })

    return True

# -------------------
# Streamlit UI
# -------------------

st.title("🧠 Image Analysis Agent")

# Sidebar: Session Controls
with st.sidebar:
    st.header("Session Control")

    if st.session_state.session_id:
        st.success(f"Session ID: {st.session_state.session_id}")
        if st.button("🔁 Start New Session"):
            create_session()
    else:
        if st.button("➕ Create Session"):
            create_session()

    st.divider()
    st.caption("Make sure `adk api_server` is running on port 8000.")

# Chat Display
st.subheader("Chat History")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("image_bytes"):
            st.image(msg["image_bytes"], caption="Uploaded Image", width=300)

# Message Input
import uuid

if "file_upload_key" not in st.session_state:
    st.session_state.file_upload_key = str(uuid.uuid4())

if st.session_state.session_id:
    user_input = st.chat_input("Type your message...")

    # ⬅️ Use key to control uploader reset
    uploaded_image = st.file_uploader("Upload an image (optional)", type=["jpg", "jpeg", "png"], key=st.session_state.file_upload_key)

    if user_input:
        send_message(user_input, uploaded_image)

        # ✅ Reset uploader key after sending message
        st.session_state.file_upload_key = str(uuid.uuid4())

        st.rerun()
else:
    st.info("👈 Please create a session to begin chatting.")
