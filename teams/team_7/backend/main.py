from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from llm import chat_with_llm, chat_with_llm_stream
from text_to_speech import text_to_speech

app = FastAPI(title="OncoGuide Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    simplified_explanation: bool = False
    tone: str | None = None
    profile: dict | None = None


class TTSRequest(BaseModel):
    text: str


@app.get("/")
def read_root():
    return {"message": "Welcome to SocialNet Backend"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/chat")
async def chat(request: ChatRequest):
    result = await chat_with_llm(
        request.message,
        request.simplified_explanation,
        tone=request.tone,
        profile=request.profile,
    )
    return result


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        async for chunk in chat_with_llm_stream(
            request.message,
            request.simplified_explanation,
            tone=request.tone,
            profile=request.profile,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/tts")
def tts(request: TTSRequest):
    audio_bytes = text_to_speech(request.text)
    return Response(content=audio_bytes, media_type="audio/mpeg")
