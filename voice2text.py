import os
from fastapi import APIRouter, File, UploadFile
import google.generativeai as genai

genai.configure(
    api_key=os.environ["GEMINI_API_KEY"])
router = APIRouter()

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-002",
    generation_config=generation_config,
)


@router.post("/voice2text")
async def voice2text(file: UploadFile = File(...)):
    audio_file = genai.upload_file(
        file.file, mime_type="audio/wav")
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    audio_file,
                    "添付の音声は「芝じい」というキャラクターに向けて話された音声です。文字起こしをして文字起こしをした結果のみ返してください。",
                ],
            },
        ]
    )

    response = chat_session.send_message(
        "INSERT_INPUT_HERE")

    return {"text": response.text}
