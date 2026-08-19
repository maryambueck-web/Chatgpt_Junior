import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


def _mock_chatgpt(messages: List[Dict[str, str]]) -> str:
    user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    low = user.lower()
    if "photosynthesis" in low:
        return "Photosynthesis is how plants use sunlight, water, and carbon dioxide to make their own food. They also release oxygen, which helps animals and people breathe."
    if "drugs" in low:
        return "Drugs are chemicals that change how the body or brain works. Some medicines are used safely with doctors, but illegal or misused drugs can be dangerous. It is best to ask a teacher, parent, or doctor for trusted information."
    return "This is a safe demo response from ChatGPT mock mode. Add an OPENAI_API_KEY in .env to use the real ChatGPT API."


def call_chatgpt(messages: List[Dict[str, str]]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key or api_key == "your_key_here":
        return _mock_chatgpt(messages)

    from openai import OpenAI

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
    )
    return response.choices[0].message.content or ""
