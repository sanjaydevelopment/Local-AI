import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt
from io import StringIO
import requests

# ---- AI Summary using Ollama ---------
def summarize_with_ollama(log_text, model="llama3"):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": f"Summarize the following system logs. Extract key insights, events, errors, warnings, repeated patterns, and generate a human-readable summary:\n\n{log_text}",
                "stream": False
            }
        )
        return response.json()["response"]
    except Exception as e:
        return f"⚠️ Error contacting Ollama: {e}"

def parse_log(file):
    try:
        decoded = file.read().decode("utf-8")
    except UnicodeDecodeError:
        file.seek(0)
        decoded = file.read().decode("latin1")

    buffer = StringIO(decoded)
    log_data = []

    # List of common regex patterns for various log formats
    patterns = [
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.+)',  # Format: 2025-04-20 12:35:30 [INFO] Log message
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) +\[(.*?)\] - (.+)',  # Format: 2017-07-04 14:32:45,179 - INFO [Thread:3] - Log message
        r'(\w+) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (.+)',  # Format: ERROR - 2025-04-20 12:35:30 - Log message
    ]

    for line in buffer:
        line = line.strip()
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) == 3:
                    timestamp, level, message = match.groups()
                    thread = "N/A"
                elif len(match.groups()) == 4:
                    timestamp, level, thread, message = match.groups()
                log_data.append({
                    'timestamp': timestamp,
                    'level': level.upper(),
                    'thread': thread,
                    'message': message
                })
                break  # Exit the loop once a match is found

    return pd.DataFrame(log_data)

# ---- Error Trend Plot ----
def plot_error_trends(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    error_df = df[df['level'] == 'ERROR']
    trend = error_df.groupby(pd.Grouper(key='timestamp', freq='H')).size()

    plt.figure(figsize=(10, 4))
    trend.plot(marker='o', color='red')
    plt.title('🕒 Error Trend Over Time')
    plt.xlabel('Time')
    plt.ylabel('Error Count')
    plt.xticks(rotation=45)
    plt.grid(True)
    st.pyplot(plt)

# ---- Streamlit App ----
st.set_page_config(page_title="AI Log Summarizer (Generic Logs)", layout="wide")
st.title("🧠 Smart Log Summarizer (Generic Log Formats)")

uploaded_file = st.file_uploader("📁 Upload your log file", type=['log', 'txt'])

if uploaded_file:
    df = parse_log(uploaded_file)

    if df.empty:
        st.warning("⚠️ Couldn’t parse any log lines. Make sure the log format matches one of the supported formats.")
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Combine into log text for Ollama summarization
        log_text = "\n".join(df.apply(lambda row: f"{row['timestamp']} [{row['level']}] {row['message']}", axis=1))

        with st.spinner("🤖 Generating summary using Ollama..."):
            summary = summarize_with_ollama(log_text)

        st.subheader("📋 AI-Generated Summary")
        st.markdown(summary)

        st.subheader("📈 Error Trend")
        plot_error_trends(df)

        search = st.text_input("🔍 Search logs")
        if search:
            results = df[df['message'].str.contains(search, case=False, na=False)]
            st.write(f"Found {len(results)} result(s)")
            st.dataframe(results, use_container_width=True)

        with st.expander("📜 View Recent Logs"):
            st.dataframe(df.tail(10), use_container_width=True)
