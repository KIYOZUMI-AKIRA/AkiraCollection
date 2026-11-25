# Langsmith会自动托管agent的记忆，无需再添加checkpointer
# 环境准备
import psycopg
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_tavily import TavilySearch
from PersonalChief.app.common.logger import logger
from langchain.messages import HumanMessage, AIMessage

load_dotenv()

# 定义工具
web_search = TavilySearch(
    max_result=5,
    topic='general'
)

# 提示词
sys_prompt = """
你是一名私人厨师。收到用户提供的食材照片或清单后，请按以下流程操作：
-识别和评估食材：若用户提供照片，首先辨识所有可见食材。基于食材的外观状态，评估其新鲜度与可用量，整理出一份“当前可用食材清单”。
-智能食谱检索：先调用 web_search 工具，以“可用食材清单”为核心关键词，查找可行菜谱。
-多维度评估与排序：从营养价值和制作难度两个维度对检索到的候选食谱进行量化打分，并根据得分排序，制作简单且营养丰富的排名靠前。
-结构化方案输出：把排序后的食谱整理为一份结构清晰的建议报告，要包含食谱信息、得分、推荐理由、食谱的参考图片，帮助用户快速做出决策。
请严格按照流程，严格调用 web_search 工具搜索食谱。
"""

# 添加记忆
connection = psycopg.connect(
    "postgresql://langchain:langchain@localhost:5432/langchain",
    autocommit=True,
    row_factory=dict_row
)

checkpointer = PostgresSaver(connection)

# 首次启动自动初始化 checkpoint 表（幂等，可重复执行）
checkpointer.setup()

# 创建智能体
agent = create_agent(
    model="deepseek-chat",
    tools=[web_search],
    system_prompt=sys_prompt,
    checkpointer=checkpointer
)

async def search_recipes(prompt: str, image: str, thread_id: str):
    """流式对话"""
    logger.info(f"[用户] : {prompt}, image: {image}, thread_id: {thread_id}")
    try:
        if not image or image.strip() == "":
            message = HumanMessage(content=prompt)
        else:
            message = HumanMessage(content=[
                {"type" : "image","url":image},
                {"type" : "text","text":prompt}
            ])

        for chunk, metadata in agent.stream(
                {"messages" : [message]},
                {"configurable" : {"thread_id" : thread_id}},
            stream_mode="messages"
        ):
            if isinstance(chunk, AIMessage) and chunk.content:
                yield chunk.content

    except Exception as e:
        logger.error(f"\n[错误] : {str(e)}")
        yield "信息检索失败,试试看手动输入食物列表？"

def _extract_text(msg) -> str:
    """从消息 content 中提取文本，兼容纯文本和多模态（图片+文本）两种形式"""
    content = msg.content
    if isinstance(content, str):
        return content

    text_parts = []
    has_image = False
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif item.get("type") == "image":
                    has_image = True

    text = "\n".join(p for p in text_parts if p)
    if has_image:
        text = f"{text}\n📷 [图片]" if text else "📷 [图片]"
    return text


async def get_messages(thread_id: str):
    """获取历史消息"""
    logger.info(f"获取历史消息, thread_id: {thread_id}")

    # 根据 thread_id 查询 checkpoint
    snapshot = checkpointer.get({"configurable": {"thread_id": thread_id}})
    if not snapshot:
        return []

    channel_values = snapshot.checkpoint.get("channel_values") or {}
    messages = channel_values.get("messages", [])
    if not messages:
        return []

    result = []
    for msg in messages:
        text = _extract_text(msg)
        if not text:
            continue

        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": text})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": text})
        # ToolMessage 等中间过程消息不返回给前端

    return result

async def clear_messages(thread_id: str):
    """清空历史消息"""
    logger.info(f"清空历史消息, thread_id: {thread_id}")
    checkpointer.delete_thread(thread_id)