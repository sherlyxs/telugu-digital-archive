# Telugu Digital Archive App with Combined AV Recording and Upload Options

import os
import uuid
from datetime import datetime

import av
import cv2
import numpy as np
import pandas as pd
import soundfile as sf
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase, VideoProcessorBase

# Directories
AUDIO_DIR = "audio_clips"
VIDEO_DIR = "video_clips"
TEXT_DIR = "text_uploads"
IMAGE_DIR = "image_uploads"
DATA_FILE = "submissions.csv"

for folder in [AUDIO_DIR, VIDEO_DIR, TEXT_DIR, IMAGE_DIR]:
    os.makedirs(folder, exist_ok=True)

# Page config
st.set_page_config(page_title="Telugu Digital Archive", layout="wide")
st.title("\U0001F4DA Telugu Digital Archive")

# Session state
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())[:8]

if "recorded_audio" not in st.session_state:
    st.session_state.recorded_audio = None

if "recorded_video" not in st.session_state:
    st.session_state.recorded_video = None

# User Info
st.markdown("### \U0001F9D1‍\U0001F4BB User Information")
name = st.text_input("\U0001F464 Enter your name:")
category = st.selectbox("\U0001F4C2 Select a category:", ["News", "Culture", "Health", "Personal", "Other"])
english_prompt = st.text_area("\U0001F4DD English Prompt (optional):")
telugu_response = st.text_area("✍ Telugu Response (optional):")

# Upload Section
st.markdown("---")
st.subheader("\U0001F4E4 Upload Pre-recorded Files")

uploaded_audio = st.file_uploader("\U0001F3A7 Upload Audio (WAV)", type=["wav"])
uploaded_video = st.file_uploader("\U0001F3A5 Upload Video (MP4)", type=["mp4"])
uploaded_image = st.file_uploader("\U0001F5BC Upload Image", type=["jpg", "jpeg", "png"])
uploaded_text = st.file_uploader("\U0001F4C4 Upload Text Document", type=["txt", "pdf", "docx"])

if uploaded_audio:
    audio_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4().hex}.wav")
    with open(audio_path, "wb") as f:
        f.write(uploaded_audio.read())
    st.session_state.recorded_audio = audio_path
    st.audio(audio_path)

if uploaded_video:
    video_path = os.path.join(VIDEO_DIR, f"{uuid.uuid4().hex}_{uploaded_video.name}")
    with open(video_path, "wb") as f:
        f.write(uploaded_video.read())
    st.session_state.recorded_video = video_path
    st.video(video_path)

if uploaded_image:
    image_path = os.path.join(IMAGE_DIR, f"{uuid.uuid4().hex}_{uploaded_image.name}")
    with open(image_path, "wb") as f:
        f.write(uploaded_image.read())
    st.image(image_path, caption="Uploaded Image", use_column_width=True)

if uploaded_text:
    text_path = os.path.join(TEXT_DIR, f"{uuid.uuid4().hex}_{uploaded_text.name}")
    with open(text_path, "wb") as f:
        f.write(uploaded_text.read())
    st.markdown(f"\U0001F4C1 {uploaded_text.name} saved.")

# Combined AV Capture
st.markdown("---")
st.subheader("\U0001F3A5\U0001F399 Record Audio + Video")

class AVProcessor(VideoProcessorBase, AudioProcessorBase):
    def _init_(self):
        self.video_frames = []
        self.audio_frames = []

    def recv(self, frame):
        self.video_frames.append(frame.to_ndarray(format="bgr24"))
        return frame

    def recv_audio(self, frame):
        self.audio_frames.append(frame.to_ndarray())
        return frame

    def get_audio(self):
        if self.audio_frames:
            return np.concatenate(self.audio_frames, axis=1).T.astype("float32")
        return None

    def get_video(self):
        return self.video_frames

ctx = webrtc_streamer(
    key="av-capture",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={"video": True, "audio": True},
    video_processor_factory=AVProcessor,
    async_processing=True,
)

if st.button("\U0001F4BE Save Recording"):
    if ctx and ctx.state and ctx.state.playing:
        avp = ctx.video_processor
        if avp:
            video_frames = avp.get_video()
            audio_data = avp.get_audio()

            if video_frames:
                h, w, _ = video_frames[0].shape
                vid_path = os.path.join(VIDEO_DIR, f"{uuid.uuid4().hex}.mp4")
                out = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc(*"mp4v"), 15, (w, h))
                for f in video_frames:
                    out.write(f)
                out.release()
                st.session_state.recorded_video = vid_path
                st.success(f"\U0001F39E Video saved: {vid_path}")
                st.video(vid_path)
                with open(vid_path, "rb") as f:
                    st.download_button("⬇ Download Video", f, file_name="recorded_video.mp4", mime="video/mp4")

            if audio_data is not None:
                aud_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4().hex}.wav")
                sf.write(aud_path, audio_data, samplerate=48000, format="WAV", subtype="PCM_16")
                st.session_state.recorded_audio = aud_path
                st.success(f"\U0001F3B5 Audio saved: {aud_path}")
                st.audio(aud_path)
                with open(aud_path, "rb") as f:
                    st.download_button("⬇ Download Audio", f, file_name="recorded_audio.wav", mime="audio/wav")

# Submit Section
st.markdown("---")
if st.button("✅ Submit Entry"):
    audio_path = st.session_state.get("recorded_audio")
    video_path = st.session_state.get("recorded_video")

    if not name.strip():
        st.error("Please enter your name before submitting.")
    elif not (audio_path or video_path or uploaded_image or uploaded_text):
        st.error("Please provide at least one form of content (upload or recording).")
    else:
        new_data = {
            "User ID": st.session_state.user_id,
            "Name": name.strip(),
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Category": category,
            "English Prompt": english_prompt.strip(),
            "Telugu Response": telugu_response.strip(),
            "Audio Path": audio_path if audio_path else "",
            "Video Path": video_path if video_path else "",
        }

        df_new = pd.DataFrame([new_data])
        if os.path.exists(DATA_FILE):
            df_existing = pd.read_csv(DATA_FILE)
            df_all = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_all = df_new

        df_all.to_csv(DATA_FILE, index=False)
        st.success("\U0001F389 Submission Saved!")

        st.subheader("\U0001F4CB Your Submission Summary")
        st.write(new_data)

        if audio_path: st.audio(audio_path)
        if video_path and os.path.exists(video_path): st.video(video_path)

        # Reset
        st.session_state.recorded_audio = None
        st.session_state.recorded_video = None

# Download Section
st.markdown("---")
st.subheader("⬇ Download Full Dataset")
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "rb") as f:
        st.download_button("Download CSV", f, "telugu_archive_submissions.csv", "text/csv")