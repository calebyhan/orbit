# ORBIT — Gemini Batch Prompt

*Last edited: YYYY-MM-DDTHH:MM:SS-05:00*

## Format

**File format:** JSONL (one JSON object per line)  
**API:** Google Gemini Batch API  
**Model:** `gemini-1.5-flash` (free tier)

---

## Structure

Each line is a JSON object with:

```json
{
  "custom_id": "unique_identifier_string",
  "method": "POST",
  "url": "/v1/models/gemini-1.5-flash:generateContent",
  "body": {
    "contents": [
      {
        "parts": [
          {
            "text": "PROMPT GOES HERE"
          }
        ]
      }
    ],
    "generationConfig": {
      "temperature": 0.0,
      "maxOutputTokens": 100,
      "responseMimeType": "application/json",
      "responseSchema": {
        "type": "object",
        "properties": {
          "field1": {"type": "string"},
          "field2": {"type": "number"}
        },
        "required": ["field1", "field2"]
      }
    }
  }
}
```

---

## Example: News Sentiment Escalation

```jsonl
{"custom_id":"news_12345","method":"POST","url":"/v1/models/gemini-1.5-flash:generateContent","body":{"contents":[{"parts":[{"text":"Analyze this financial news headline for sentiment (-1 negative to +1 positive):\n\nHeadline: Fed Holds Rates Steady Amid Inflation Concerns\nSummary: The Federal Reserve kept interest rates unchanged at its latest meeting...\n\nReturn JSON: {\"sentiment\": <float>, \"confidence\": <float 0-1>}"}]}],"generationConfig":{"temperature":0.0,"maxOutputTokens":50,"responseMimeType":"application/json","responseSchema":{"type":"object","properties":{"sentiment":{"type":"number"},"confidence":{"type":"number"}},"required":["sentiment","confidence"]}}}}
{"custom_id":"news_12346","method":"POST","url":"/v1/models/gemini-1.5-flash:generateContent","body":{"contents":[{"parts":[{"text":"Analyze this financial news headline for sentiment (-1 negative to +1 positive):\n\nHeadline: Tech Stocks Surge on Strong Earnings\nSummary: Major tech companies reported better-than-expected quarterly results...\n\nReturn JSON: {\"sentiment\": <float>, \"confidence\": <float 0-1>}"}]}],"generationConfig":{"temperature":0.0,"maxOutputTokens":50,"responseMimeType":"application/json","responseSchema":{"type":"object","properties":{"sentiment":{"type":"number"},"confidence":{"type":"number"}},"required":["sentiment","confidence"]}}}}
```

---

## Example: Reddit Sarcasm Detection

```jsonl
{"custom_id":"social_abc123","method":"POST","url":"/v1/models/gemini-1.5-flash:generateContent","body":{"contents":[{"parts":[{"text":"Is this Reddit post sarcastic?\n\nTitle: SPY calls printing today 🚀\nBody: Fed decision was bullish, obviously going to 500 tomorrow.\n\nReturn JSON: {\"sarcastic\": <bool>, \"sentiment\": <float -1 to 1>}"}]}],"generationConfig":{"temperature":0.0,"maxOutputTokens":50,"responseMimeType":"application/json","responseSchema":{"type":"object","properties":{"sarcastic":{"type":"boolean"},"sentiment":{"type":"number"}},"required":["sarcastic","sentiment"]}}}}
```

---

## Usage

### 1. Generate Batch File

```python
import json
with open('batch_input.jsonl', 'w') as f:
    for item in escalation_items:
        prompt_obj = {
            "custom_id": item["id"],
            "method": "POST",
            "url": "/v1/models/gemini-1.5-flash:generateContent",
            "body": {
                "contents": [{"parts": [{"text": construct_prompt(item)}]}],
                "generationConfig": {...}
            }
        }
        f.write(json.dumps(prompt_obj) + '\n')
```

### 2. Submit to API

```bash
curl -X POST \
  -H "Authorization: Bearer $GEMINI_API_KEY" \
  -F file=@batch_input.jsonl \
  https://generativelanguage.googleapis.com/v1/batches
```

### 3. Poll for Results

Results returned as JSONL with matching `custom_id`.

---

## Rate Limits

- **Free tier:** 15 RPM, 1M TPM, 1500 RPD
- **Batch jobs:** Processed asynchronously (may take minutes to hours)

---

## Related Files

* `04-data-sources/gemini_sentiment_api.md`
* `05-ingestion/llm_batching_gemini.md`

---

