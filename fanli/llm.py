"""OpenAI 兼容接口的 LLM 客户端（DeepSeek、通义千问等均可）。

没有配置密钥时 available() 返回 False，调用方走离线降级路径，保证流程能跑通。
"""
import os

_client = None


def _load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


def available():
    return bool(os.environ.get("LLM_API_KEY"))


def model_name():
    return os.environ.get("LLM_MODEL", "deepseek-chat")


def chat(system, user, temperature=0.2):
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
        )
    resp = _client.chat.completions.create(
        model=model_name(),
        temperature=temperature,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    usage = getattr(resp, "usage", None)
    if usage is not None:
        _log_usage(usage.prompt_tokens, usage.completion_tokens)
    return resp.choices[0].message.content


def _log_usage(prompt_tokens, completion_tokens):
    os.makedirs("results", exist_ok=True)
    with open(os.path.join("results", "token_usage.csv"), "a", encoding="utf-8") as f:
        f.write(f"{model_name()},{prompt_tokens},{completion_tokens}\n")
