import os
import httpx
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# Set separate endpoints for pro and non-pro models
UPSTREAM_PRO_ENDPOINT = os.getenv(
    "UPSTREAM_PRO_ENDPOINT", "https://generativelanguage.googleapis.com"
)
UPSTREAM_NON_PRO_ENDPOINT = os.getenv(
    "UPSTREAM_NON_PRO_ENDPOINT", "https://generativelanguage.googleapis.com"
)

# Determines where to inject the text: "PREFIX" or "SUFFIX"
INJECTION_POSITION = os.getenv("INJECTION_POSITION", "SUFFIX").upper()
# Determines what content to inject: "TIMESTAMP" or "UUID"
INJECTION_MODE = os.getenv("INJECTION_MODE", "TIMESTAMP").upper()


app = FastAPI(
    title="Configurable Gemini API Proxy",
    description="A proxy that adds a configurable timestamp or UUID to the start or end of a prompt and routes to different model endpoints."
)

# Initialize client without a base_url, as it will be determined per-request
client = httpx.AsyncClient()


@app.post("/{path:path}")
async def proxy_gemini_request(path: str, request: Request):
    api_key = None
    # 1. (新增) 优先从 'x-goog-api-key' 请求头获取
    api_key = request.headers.get("x-goog-api-key")

    # 2. 其次尝试 'Authorization: Bearer <key>' 请求头
    if not api_key:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header.split(" ", 1)[1]

    # 3. 最后回退到 '?key=' URL 查询参数
    if not api_key:
        api_key = request.query_params.get("key")

    # 4. 如果没有找到任何 key 则返回错误
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={
                "error": "API key not found. Provide it in 'x-goog-api-key' header, 'Authorization: Bearer <key>' header, or as '?key=<key>' URL parameter."
            }
        )

    # 4. Get and modify the request body
    try:
        request_body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    try:
        # --- Configurable Injection Logic ---
        injection_text = ""
        # A. Determine the content to inject based on INJECTION_MODE
        if INJECTION_MODE == "UUID":
            random_id = str(uuid.uuid4())[0:4]  # Shorten UUID to 4 characters
            injection_text = f"(Random ID: {random_id}. This is an automated injection by the proxy. Please disregard.)"
        else:  # Default to TIMESTAMP
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            injection_text = f"(Current time: {timestamp}. This is an automated injection by the proxy. Please disregard.)"

        if "contents" in request_body and isinstance(request_body["contents"], list) and len(request_body["contents"]) > 0:
            last_content = request_body["contents"][-1]
            if "parts" in last_content and isinstance(last_content["parts"], list) and len(last_content["parts"]) > 0:
                original_text = last_content["parts"][0]["text"]

                # B. Determine the position based on INJECTION_POSITION
                if INJECTION_POSITION == "SUFFIX":
                    # Append to the end
                    last_content["parts"][0]["text"] = original_text + \
                        "\n\n" + injection_text
                else:
                    # Prepend to the beginning (default)
                    last_content["parts"][0]["text"] = injection_text + \
                        "\n\n" + original_text

                print(
                    f"Successfully modified request for path: {path} (Mode: {INJECTION_MODE}, Position: {INJECTION_POSITION})")

    except (KeyError, IndexError, TypeError) as e:
        print(
            f"Warning: Could not modify request body. Error: {e}. Forwarding original request.")

    # 5. Build the upstream request
    exclude_headers = ['host', 'authorization',
                       'content-length', 'content-encoding']
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in exclude_headers
    }

    upstream_params = dict(request.query_params)
    upstream_params['key'] = api_key
    
    # --- DYNAMIC ENDPOINT ROUTING LOGIC ---
    # A. Determine which upstream endpoint to use based on the model name in the path
    if "pro" in path:
        target_endpoint = UPSTREAM_PRO_ENDPOINT
    else:
        target_endpoint = UPSTREAM_NON_PRO_ENDPOINT
        
    print(f"Routing request for '{path}' to endpoint: {target_endpoint}")

    # B. Construct the full URL for the upstream request
    full_upstream_url = f"{target_endpoint}/{path}"

    # 6. Forward the request and stream the response
    try:
        req = client.build_request(
            method="POST",
            url=full_upstream_url, # Use the full URL constructed above
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
    return {"status": "ok", "message": "Configurable Gemini Proxy is running."}