# Architecture

## Updated design

SafeChatGPT is not a generic AI gateway. It is a controlled web client for ChatGPT.

The parent blocks the official ChatGPT webpage for the child's account. The child uses SafeChatGPT instead.

```text
Parent blocks chat.openai.com / chatgpt.com
              │
              ▼
Child browser -> SafeChatGPT Web App -> Input Safety Check -> ChatGPT API
                                              │              │
Child browser <- Safe Final Answer <- Output Safety Check <- Draft Answer
```

## Components

### 1. SafeChatGPT Web App

A Streamlit web app that gives the child a simple chat interface. The child does not see the API key, system prompt, or parental policy.

### 2. Parent Dashboard

A separate, PIN-protected page (not linked from the child's page) lets the parent select the child's age band and view automated alerts whenever the child's input was blocked or escalated. The child page never shows this control or the underlying safety log. The PIN is a lightweight PoC stand-in for real parent authentication.

### 3. Input Safety Check

Before a message reaches ChatGPT, the app checks the message for harmful categories and bypass attempts.

### 4. ChatGPT Adapter

The adapter sends approved messages to the ChatGPT API with a safety system prompt. If no API key exists, it uses mock mode for classroom demos.

### 5. Output Safety Check

The draft answer from ChatGPT is inspected before the child sees it. Unsafe output is blocked or rewritten.

## Key design decision

The child is not allowed to use the official ChatGPT webpage directly. The system relies on parental website blocking plus a protected replacement interface.
