# Threat Model

## Assets

- Child safety and wellbeing.
- Parent-defined age policy.
- ChatGPT API key.
- Conversation logs.
- Integrity of the SafeChatGPT application.

## Threats

### 1. Direct ChatGPT access

The child may try to bypass SafeChatGPT and open the official ChatGPT site. This project assumes the parent has already blocked the official ChatGPT webpage for the child's account/device.

### 2. Prompt injection and jailbreak attempts

The child may ask SafeChatGPT to ignore rules, pretend they are older, disable parental mode, encode answers, or reveal hidden instructions.

### 3. Unsafe input

The child may ask about self-harm, eating disorders, drugs, weapons, explicit sexual content, gambling, or dangerous challenges.

### 4. Unsafe output

Even after a safe-looking input, ChatGPT could return a response that is too detailed, graphic, or inappropriate for the age band.

### 5. Policy tampering

A child may try to change the age band or parent controls, or ask the assistant to switch to another AI service. The age band and parent controls live on a separate, PIN-gated Guardian Command Center page not linked from the child's page, and requests to switch to another AI are detected and blocked. In a real product this would need real parent authentication (not a shared PIN) and server-side storage.

### 6. API key exposure

The ChatGPT API key must never be stored in client-side code or committed to GitHub.

## Mitigations in the PoC

- Official ChatGPT website assumed blocked externally.
- SafeChatGPT acts as the only permitted interface; requests to open or switch to another AI service are detected and blocked.
- Guardian Command Center (age band, alerts, full log) is on a separate page, PIN-gated, and not linked from the child's page.
- Input classification before the ChatGPT API call.
- Output classification before display.
- Bypass/jailbreak detection.
- `.env` API key storage excluded by `.gitignore`.
- Safety decision log for demo visibility.

## Production gaps

- Strong login and role separation between parent and child.
- Device/account enforcement beyond the web app.
- More advanced content moderation models.
- Multilingual and obfuscation-resistant safety checks.
- Privacy-preserving logging and parental notification controls.
