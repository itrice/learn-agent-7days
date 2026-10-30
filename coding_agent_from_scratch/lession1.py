from dotenv import load_dotenv

import os
import json
from openai import OpenAI

load_dotenv()

# ========== 0. 从环境变量读取配置 ==========
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")  # 可选，不设置则用 OpenAI 官方
model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # 可选，给个默认值

if not api_key:
    raise RuntimeError("未找到环境变量 OPENAI_API_KEY，请先设置它。")

client = OpenAI(
    api_key=api_key,
    base_url=base_url,  # 如果为 None，openai SDK 会自动用官方地址
)

# ========== 1. 工具函数 ==========


def get_order_status(order_id: str) -> str:
    """查询订单状态。当用户询问某个订单的物流/发货情况时使用。"""
    db = {"4471": "已发货，UPS承运，预计2天送达"}
    return db.get(order_id, "未找到该订单")


def calculate(expression: str) -> str:
    """计算数学表达式。当用户需要做算术运算时使用。"""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"计算失败: {e}"


# ========== 2. 工具 schema ==========
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "查询订单状态。当用户询问某个订单的物流或发货情况时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号，例如 4471"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式。当用户需要做算术运算时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "要计算的表达式，如 3.5*8"}
                },
                "required": ["expression"],
            },
        },
    },
]

TOOL_MAP = {
    "get_order_status": get_order_status,
    "calculate": calculate,
}


def execute_tool(name: str, args: dict) -> str:
    func = TOOL_MAP.get(name)
    if not func:
        return f"未知工具: {name}"
    return func(**args)


def run_agent(input: str):
    turns = 0
    messages = [{"role": "user", "content": input}]

    MAX_TURNS = 5
    while turns < MAX_TURNS:
        turns += 1
        print("===send to LLM===\n", messages)
        # 1. 真正调用 LLM
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=TOOLS_SCHEMA,
        )

        msg = response.choices[0].message

        if msg.tool_calls:
            messages.append(msg)

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                result = execute_tool(name, args)

                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call.id,
                })
        else:
            print(msg.content)
            break

    else:
        print("达到最大轮数，结束对话。")


# ========== 3. 测试 ==========
if __name__ == "__main__":
    print("当前 model:", model_name)
    print("当前 base_url:", base_url or "(OpenAI 官方默认)")
    print("直接调用工具:", get_order_status("4471"))
    print("直接调用工具:", get_order_status("5471"))
    print("直接调用工具:", calculate("3.5*8"))
    print("execute tool:", execute_tool(
        "get_order_status", {"order_id": "4471"}))
    print("execute tool:", execute_tool("get_name", {"order_id": "4471"}))
    run_agent("帮我查下5471号订单状态，并算下 99 乘以 8 是多少")
