import os
import httpx
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
UPSTREAM_GEMINI_ENDPOINT = os.getenv("UPSTREAM_GEMINI_ENDPOINT", "https://generativelanguage.googleapis.com")

app = FastAPI(
    title="Gemini API Compatible Proxy",
    description="A proxy that mirrors Google Gemini's auth, adds a timestamp, and supports streaming."
)

client = httpx.AsyncClient(base_url=UPSTREAM_GEMINI_ENDPOINT)

@app.post("/{path:path}")
async def proxy_gemini_request(path: str, request: Request):
    api_key = None

    # 1. Prioritize Authorization header for API Key
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        api_key = auth_header.split(" ", 1)[1]

    # 2. Fallback to '?key=' query parameter
    if not api_key:
        api_key = request.query_params.get("key")

    # 3. Return error if no key is found
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"error": "API key not found. Provide it in 'Authorization: Bearer <key>' header or as '?key=<key>' URL parameter."}
        )

    # 4. Get and modify the request body
    try:
        request_body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        prefix_to_add = f"(Current time: {timestamp}. This is an automated prefix added by the proxy. Please disregard.)\n\n"
        if "contents" in request_body and isinstance(request_body["contents"], list) and len(request_body["contents"]) > 0:
            last_content = request_body["contents"][-1]
            if "parts" in last_content and isinstance(last_content["parts"], list) and len(last_content["parts"]) > 0:
                last_content["parts"][0]["text"] = prefix_to_add + last_content["parts"][0]["text"]
                print(f"Successfully prefixed the request for path: {path}")
    except (KeyError, IndexError, TypeError) as e:
        print(f"Warning: Could not modify request body. Error: {e}. Forwarding original request.")

    # 5. Build the upstream request, ensuring original query parameters are preserved.
    # --- THIS IS THE FIX ---
    # Exclude headers that can cause issues when the body is modified.
    # httpx will correctly recalculate Content-Length.
    exclude_headers = ['host', 'authorization', 'content-length', 'content-encoding']
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in exclude_headers
    }
    
    # Prepare upstream request parameters, ensuring our extracted API key is used.
    upstream_params = dict(request.query_params)
    upstream_params['key'] = api_key

    # 6. Forward the request and stream the response
    try:
        req = client.build_request(
            method="POST",
            url=f"/{path}",
            params=upstream_params,
            json=request_body,
            headers=headers,
            timeout=300
        )
        upstream_response = await client.send(req, stream=True)

        return StreamingResponse(
            upstream_response.aiter_bytes(),
            status_code=upstream_response.status_code,
            media_type=upstream_response.headers.get("content-type")
        )
    except httpx.RequestError as e:
        return JSONResponse(status_code=502, content={"error": f"Upstream request failed: {e}"})

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Gemini Compatible Proxy is running."}