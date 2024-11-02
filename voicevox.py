import requests
import os
import json
import re


def create_wav(text: str, speaker_id: str) -> bytes:
    # 感情タグの抽出
    emotion = re.search(r'\[(.*)\]', text)
    if emotion:
        emotion = emotion.group(1)
    else:
        emotion = "normal"
    text = text.replace(f"[{emotion}]", "")

    base_url = os.getenv(
        "VOICEVOX_URL", "http://localhost:50021")
    params = (
        ("text", text),
        ("speaker", int(speaker_id)),
    )
    response = requests.post(
        f"{base_url}/audio_query", params=params)
    audio_query = response.json()
    synthesis = requests.post(
        f'{base_url}/synthesis',
        headers={
            "Content-Type": "application/json"},
        params=params,
        data=json.dumps(audio_query)
    )
    return synthesis.content
