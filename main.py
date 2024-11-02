from fastapi import FastAPI
from chat import router as chat_router
from voice2text import router as voice2text_router
from rag import router as rag_router  # 追加
app = FastAPI()

app.include_router(chat_router)
app.include_router(voice2text_router)
app.include_router(rag_router)  # 追加
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
