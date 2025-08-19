[中文](./README.zh.md)

# Gemini API Uniqueness Proxy

A simple, self-hosted proxy for the Google Gemini API designed to solve a specific problem: Gemini sometimes refuses to respond to identical, consecutive prompts.

## The Problem

When making multiple, identical API requests to the Gemini API in quick succession, you might encounter situations where the API returns an empty or incomplete response. This is likely due to a server-side mechanism to prevent redundant processing or handle potential duplicate requests. For applications that might legitimately send the same prompt multiple times (e.g., for testing, or in stateless environments), this can be a significant issue.

## The Solution

This proxy intercepts your requests to the Gemini API and transparently adds a unique, high-precision timestamp to the beginning of your prompt.

**Original Prompt:**
`"What is the capital of France?"`

**Modified Prompt Sent to Gemini:**
`"(Current time: 2023-10-27 10:30:00.123. This is an automated prefix added by the proxy. Please disregard.)\n\nWhat is the capital of France?"`

This small modification makes every request unique from the perspective of the Gemini API, effectively bypassing the duplicate request filter and ensuring a consistent response. The added text is designed to be ignored by the model.

## Features

- **Automatic Prompt Uniqueness**: Injects a timestamp into each request to prevent issues with duplicate prompts.
- **Full API Compatibility**: Mirrors the Gemini API structure. You can use it as a drop-in replacement for the official API endpoint.
- **Streaming Support**: Fully supports streaming responses for a real-time experience.
- **Flexible Authentication**: Accepts the API key from either the `Authorization: Bearer <key>` header or the `?key=<key>` query parameter.
- **Easy to Deploy**: A single Python file with minimal dependencies.

## Setup and Usage

### Using Docker Compose (Recommended)

The simplest way to run this proxy is with Docker Compose.

1.  **Prerequisites**: Make sure you have Docker and Docker Compose installed.
2.  **Clone the repository.**
3.  **Configure your API Key**: The service expects your Gemini API key as an environment variable `GEMINI_API_KEY`. The recommended way is to create a `.env` file in the project root:
    ```
    # .env
    GEMINI_API_KEY="YOUR_API_KEY"
    ```
4.  **Start the service**:
    ```bash
    docker-compose up -d
    ```
The proxy will now be running on `http://localhost:8000`. You can then make requests as shown below, but you don't need to include the key in the URL or headers.

### Manual Setup

#### 1. Prerequisites

- Python 3.8+
- `pip`

#### 2. Installation

1.  Clone this repository or download the `main.py` file.

2.  Create a `requirements.txt` file (or use the one provided) with the following content:
    ```
    fastapi
    uvicorn
    httpx
    python-dotenv
    ```

3.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  (Optional) Create a `.env` file in the same directory to configure the upstream Gemini endpoint. If not provided, it defaults to `https://generativelanguage.googleapis.com`.
    ```
    # .env
    UPSTREAM_GEMINI_ENDPOINT="https://generativelanguage.googleapis.com"
    ```

#### 3. Running the Proxy

Start the proxy server using Uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The proxy will now be running on `http://localhost:8000`.

## Making Requests

Update your application or client to point to the proxy's address (`http://localhost:8000`) instead of the official Gemini API endpoint. Make sure to include your Gemini API key.

**Example using `curl`:**

```bash
curl http://localhost:8000/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY \
    -H 'Content-Type: application/json' \
    -d '{
      "contents": [{
        "parts":[{
          "text": "Write a story about a magic backpack."
        }]
      }]
    }'
```

The proxy will forward this request to Gemini with the added timestamp and stream the response back to you.