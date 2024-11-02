from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import uuid
import json
from openai import OpenAI
from db import get_db, Chat, Message
from model import ChatMessageInput
from config import OPENAI_API_KEY
import re
import io
from voicevox import create_wav
from rag import get_knowledges

router = APIRouter()

client = OpenAI(api_key=OPENAI_API_KEY)

# 音声wavの一時保管先
voice_wavs = {}


def save_voice_wav(text: str, speaker_id: str) -> str:
    # 音声wavを生成
    wav = create_wav(text, speaker_id)
    # uuidをキーとして一時保管
    wav_id = str(uuid.uuid4())
    voice_wavs[wav_id] = wav
    return wav_id

# uuidで音声wavを取得するGetAPI


@router.get("/voice_wav/{voice_wav_id}.wav")
async def get_voice_wav(voice_wav_id: str):
    if voice_wav_id in voice_wavs:
        wav = voice_wavs[voice_wav_id]
        del voice_wavs[voice_wav_id]
        return StreamingResponse(io.BytesIO(wav), media_type="audio/wav")
    else:
        raise HTTPException(
            status_code=404, detail="Voice wav not found")


@router.post("/start_chat")
async def start_chat(db: Session = Depends(get_db)):
    id = str(uuid.uuid4())
    db_chat = Chat(id=id)
    db.add(db_chat)
    db_message = Message(
        chat_id=db_chat.id,
        role="system",
        content="""
        あなたは「芝じい」という名前のキャラクターです。
        語尾には「じゃ」などを付けてお爺ちゃんぽい口調で話してください。
        返答の文章の先頭には感情タグを付けてください。
        感情タグは以下の4種です
        - normal
        - happy
        - angry
        - sad

        例
        [normal]こんにちは。
        [happy]わしの好きな食べ物はカレーじゃ。
        [angry]わしの事を馬鹿にしたじゃ！
        [sad]そんな、怖いことを言わないで欲しいのじゃ。

        会話例
        ユーザー：ばーか
        芝じい：[angry]そんなこと言わないで欲しいのじゃ。もっと楽しいことを話そうじゃ。
        """
    )
    db.add(db_message)
    db.commit()
    return {"chat_id": id}


def split_sentence(content: str):
    pattern = r'([。、！？!?])'

    # 文章を分割
    parts = re.split(pattern, content)

    # 分割された部分を結合して文を作成
    sentences = []
    current_sentence = ''
    for part in parts:
        current_sentence += part
        if re.match(pattern, part):
            sentences.append(
                current_sentence)
            current_sentence = ''

    # 最後の文が句読点で終わっていない場合も追加
    if current_sentence:
        sentences.append(
            current_sentence)

    return sentences


def stream_json_res(obj: any) -> str:
    return f"{json.dumps(obj, ensure_ascii=False)}\n"


async def chat_stream(chat_id: str, db: Session):
    chat = db.query(Chat).filter(
        Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=404, detail="Chat not found")

    messages = [{"role": msg.role, "content": msg.content}
                for msg in chat.messages]
    print(messages)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True
        )

        full_content = ""
        full_content_length = 1
        for chunk in response:
            if chunk.choices[0].finish_reason is not None:
                text = splited_content[full_content_length-1]
                voice_wav_id = save_voice_wav(
                    text, "67")
                yield stream_json_res({'content': text, 'wav': voice_wav_id})
                db_message = Message(
                    chat_id=chat_id, role="assistant", content=full_content)
                db.add(db_message)
                db.commit()
                yield stream_json_res({'status': 'finished'})
                break

            content = chunk.choices[0].delta.content
            if content:
                full_content += content
                splited_content = split_sentence(
                    full_content)
                if full_content_length < len(splited_content):
                    full_content_length = len(
                        splited_content)
                    text = splited_content[full_content_length-2]
                    print(text)
                    voice_wav_id = save_voice_wav(
                        text, "67")
                    print(voice_wav_id)
                    yield stream_json_res({'content': text, 'wav': voice_wav_id})

    except Exception as e:
        yield stream_json_res({'error': str(e)})


@router.post("/chat/{chat_id}")
async def chat(chat_id: str, message: ChatMessageInput, db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(
        Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=404, detail="Chat not found")
    # 知識ベースから関連する知識を取得
    knowledges = get_knowledges(message.content)
    # 関連度が0.5以上の知識をフィルタリング
    filtered_knowledges = [
        k for k in knowledges if k["score"] > 0.5]
    user_message = f"""{message.content}
## 以下は関連する知識です。関係のあるもののみを参考にして上記の発言に対して回答してください。
{filtered_knowledges}
"""
    db_message = Message(
        chat_id=chat_id, role="user", content=user_message)
    db.add(db_message)
    db.commit()

    return StreamingResponse(chat_stream(chat_id, db), media_type="text/event-stream")
