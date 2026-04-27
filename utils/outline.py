"""Generate structured content outline from transcription using LLM"""
import json
import urllib.request
import urllib.error
import os


LLM_BASE_URL = os.environ.get("QCLAW_LLM_BASE_URL", "http://127.0.0.1:19000/proxy/llm")
LLM_API_KEY = os.environ.get("QCLAW_LLM_API_KEY", "__QCLAW_AUTH_GATEWAY_MANAGED__")


def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 2000) -> str:
    """Call QClaw LLM API
    
    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        max_tokens: Max output tokens
        
    Returns:
        LLM response text
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    url = f"{LLM_BASE_URL}/chat/completions"
    data = json.dumps({
        "model": "modelroute",
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"LLM API error: HTTP {e.code}")
    except Exception as e:
        raise RuntimeError(f"LLM API error: {e}")


def generate_outline(transcription: str, title: str = "") -> dict:
    """Generate structured content outline from transcription
    
    Args:
        transcription: Video transcription text
        title: Optional video title for context
        
    Returns:
        dict with keys: topics, summary, related_concepts
    """
    system_prompt = """你是一个内容分析助手。直接输出JSON，不要任何思考过程或解释。

重要：只输出JSON对象，不要有其他任何文字、思考过程或markdown标记。"""
    
    prompt = f"""分析以下视频转写文本，生成结构化内容大纲。

视频标题: {title}

转写文本:
{transcription}

请生成以下内容（输出为 JSON 格式）：

1. "topics": 关键知识点/主题列表（每个主题用 5-15 字概括）
2. "steps": 如果有教程/操作步骤，提取具体步骤列表（每个步骤一句话）
3. "summary": 3-5 条要点摘要（每条 1-2 句话）
4. "related_concepts": 相关概念关键词列表（用于创建 Obsidian 双向链接）

输出格式示例：
{{
  "topics": ["知识点1", "知识点2"],
  "steps": ["步骤1", "步骤2"],
  "summary": ["要点1", "要点2"],
  "related_concepts": ["概念1", "概念2"]
}}

如果文本中没有教程步骤，steps 字段可以为空数组 []。
只输出 JSON，不要其他内容。"""
    
    response = call_llm(prompt, system_prompt, max_tokens=3000)
    
    # Handle thinking response format (e.g., "<thought>...</thought>json here")
    # Try multiple extraction methods
    
    # Parse JSON from response (handle thinking blocks and markdown code blocks)
    response = response.strip()
    
    # Remove thinking blocks if present (e.g., "<thought>...</thought>")
    import re
    response = re.sub(r'<[^>]+>.*?</[^>]+>', '', response, flags=re.DOTALL)
    response = response.strip()
    
    # Remove markdown code block markers
    if response.startswith("```"):
        lines = response.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        response = "\n".join(lines).strip()
    
    # Try to find JSON object in response
    match = re.search(r'\{[\s\S]*\}', response)
    if match:
        json_str = match.group(0)
        try:
            outline = json.loads(json_str)
        except json.JSONDecodeError:
            outline = None
    else:
        outline = None
    
    if not outline:
        outline = {
            "topics": [],
            "steps": [],
            "summary": [],
            "related_concepts": []
        }
    
    return outline


def format_outline_markdown(outline: dict) -> str:
    """Format outline dict as markdown sections
    
    Args:
        outline: Outline dict from generate_outline
        
    Returns:
        Markdown formatted string
    """
    lines = []
    
    # Key topics
    if outline.get("topics"):
        lines.append("## 📌 关键知识点")
        for topic in outline["topics"]:
            lines.append(f"- {topic}")
        lines.append("")
    
    # Steps
    if outline.get("steps"):
        lines.append("## 📝 操作步骤")
        for i, step in enumerate(outline["steps"], 1):
            lines.append(f"{i}. {step}")
        lines.append("")
    
    # Summary
    if outline.get("summary"):
        lines.append("## 🎯 内容摘要")
        for point in outline["summary"]:
            lines.append(f"- {point}")
        lines.append("")
    
    # Related concepts (Obsidian wiki-links)
    if outline.get("related_concepts"):
        lines.append("## 🔗 相关概念")
        links = " ".join([f"[[{c}]]" for c in outline["related_concepts"]])
        lines.append(links)
        lines.append("")
    
    return "\n".join(lines)