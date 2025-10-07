import requests
# 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
HF_TOKEN="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"

API_URL = "https://router.huggingface.co/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

response = query({
    "messages": [
        {
            "role": "user",
            "content": (
                "Answer as a regular person. "
                "What is the most popular sport? "
                "Give a short, natural answer, no more than three sentences."
            )
        }
    ],
    "model": "Qwen/Qwen1.5-1.8B-Chat:featherless-ai",
    "max_tokens": 60,         # Ограничение длины
    "temperature": 0.8,       # Более живой стиль
    "top_p": 0.95             # (опционально) для разнообразия
})

print(response)
print(response["choices"][0]["message"])