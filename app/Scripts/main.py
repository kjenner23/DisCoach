from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
import json
import uuid
import subprocess

PROMPT_PATH = Path("app/prompts/article_to_json_prompt.txt")
PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

app = FastAPI()


def call_ollama(prompt: str) -> str:
    """Call Ollama llama3 and return raw stdout."""
    result = subprocess.run(
        ["ollama", "run", "llama3"],
        input=prompt,
        text=True,
        capture_output=True
    )
    # Optional: log stderr if something goes wrong
    if result.stderr:
        print("=== OLLAMA STDERR ===")
        print(result.stderr)
        print("=====================")
    return result.stdout


class ArticleInput(BaseModel):
    article_id: str | None = None
    text: str


@app.get("/")
def read_root():
    return {"message": "Hello Kristopher, FastAPI is running 🚀"}


@app.post("/process")
def process_article(payload: ArticleInput):
    article_id = payload.article_id or str(uuid.uuid4())

    # DEBUG: see what we really received
    #print("=== DEBUG payload.text (first 300 chars) ===")
    #print(repr(payload.text[:300]))
    #print("=== END payload.text ===")

    # Build final prompt
    prompt_final = PROMPT_TEMPLATE.replace("{{ARTICLE_TEXT}}", payload.text)

    # Guard: placeholder must be gone
    if "{{ARTICLE_TEXT}}" in prompt_final:
        raise RuntimeError(
            "Placeholder {{ARTICLE_TEXT}} still present after replace. "
            "Check the prompt file for typos or extra spaces."
        )

    # Optional: show the tail of the prompt to verify article is there
    #print("=== DEBUG prompt_final (last 400 chars) ===")
    #print(prompt_final[-400:])
    #print("=== END prompt_final ===")

    ollama_response = call_ollama(prompt_final)

    try:
        parsed = json.loads(ollama_response)
    except Exception:
        parsed = {"raw_output": ollama_response}

    out_dir = Path("processed")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{article_id}.json"
    out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2))

    return {
        "status": "ok",
        "article_id": article_id,
        "llm_output": parsed
    }
