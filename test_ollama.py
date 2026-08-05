import requests

url = "http://localhost:11434/api/chat"

payload = {
    "model": "qwen3:4b",
    "messages": [
        {
            "role": "user",
            "content": "Reply with only: Ollama is working!"
        }
    ],
    "stream": False
}

response = requests.post(url, json=payload)

print(response.status_code)
print(response.json()["message"]["content"])