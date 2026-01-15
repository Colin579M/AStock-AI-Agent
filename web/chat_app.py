"""
TradingAgents Chatbot Web 应用

基于 Streamlit 的手机友好聊天界面。
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from datetime import datetime

# 页面配置（必须在最开始）
st.set_page_config(
    page_title="股票分析助手",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 自定义 CSS（手机优化）
st.markdown("""
<style>
    /* 手机优化 */
    .stApp {
        max-width: 100%;
    }

    /* 大按钮 */
    .stButton > button {
        width: 100%;
        height: 50px;
        font-size: 18px;
        border-radius: 10px;
    }

    /* 输入框 */
    .stTextInput > div > div > input {
        font-size: 18px;
        padding: 15px;
    }

    /* 聊天消息 */
    .chat-message {
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }

    .user-message {
        background-color: #e3f2fd;
        text-align: right;
    }

    .assistant-message {
        background-color: #f5f5f5;
    }

    /* 标题 */
    h1 {
        text-align: center;
        color: #1976d2;
    }

    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化 session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chatbot" not in st.session_state:
        st.session_state.chatbot = None

    if "initialized" not in st.session_state:
        st.session_state.initialized = False


def load_chatbot():
    """加载 Chatbot"""
    if st.session_state.chatbot is None:
        try:
            from tradingagents.chatbot import ChatbotGraph
            st.session_state.chatbot = ChatbotGraph()
            st.session_state.initialized = True
            return True
        except Exception as e:
            st.error(f"初始化失败: {e}")
            return False
    return True


def check_existing_report(ticker: str, date: str) -> str:
    """检查是否有现有报告"""
    results_dir = project_root / "results" / ticker / date / "reports"

    # 按优先级查找报告
    report_files = [
        "consolidation_report.md",
        "fundamentals_report.md",
        "trader_investment_plan.md",
    ]

    for filename in report_files:
        report_path = results_dir / filename
        if report_path.exists():
            try:
                return report_path.read_text(encoding="utf-8")
            except Exception:
                continue

    return None


def display_chat_history():
    """显示聊天历史"""
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-message user-message">🧑 {msg["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="chat-message assistant-message">🤖 {msg["content"]}</div>',
                unsafe_allow_html=True
            )


def main():
    """主函数"""
    init_session_state()

    # 标题
    st.title("📈 股票分析助手")
    st.markdown("---")

    # 初始化提示
    if not st.session_state.initialized:
        with st.spinner("正在初始化..."):
            if load_chatbot():
                st.success("初始化完成！")
            else:
                st.stop()

    # 快捷功能区
    st.subheader("快捷查询")
    col1, col2 = st.columns(2)

    with col1:
        quick_ticker = st.text_input(
            "股票代码",
            placeholder="如 600036",
            max_chars=6,
            key="quick_ticker"
        )

    with col2:
        quick_action = st.selectbox(
            "查询类型",
            ["估值", "资金流向", "基本面", "完整分析"],
            key="quick_action"
        )

    if st.button("🔍 快速查询", use_container_width=True):
        if quick_ticker and len(quick_ticker) == 6:
            action_map = {
                "估值": f"{quick_ticker}的PE和PB是多少？",
                "资金流向": f"{quick_ticker}的资金流向如何？",
                "基本面": f"{quick_ticker}的基本面怎么样？",
                "完整分析": f"帮我全面分析{quick_ticker}",
            }
            query = action_map[quick_action]

            st.session_state.messages.append({"role": "user", "content": query})

            with st.spinner("分析中..."):
                response = st.session_state.chatbot.chat(query)
                st.session_state.messages.append({"role": "assistant", "content": response})

            st.rerun()
        else:
            st.warning("请输入6位股票代码")

    st.markdown("---")

    # 自由对话区
    st.subheader("自由对话")

    # 显示聊天历史
    chat_container = st.container()
    with chat_container:
        display_chat_history()

    # 输入框
    user_input = st.text_input(
        "输入问题",
        placeholder="问我任何股票问题...",
        key="user_input",
        label_visibility="collapsed"
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.button("📤 发送", use_container_width=True):
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})

                with st.spinner("思考中..."):
                    response = st.session_state.chatbot.chat(user_input)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                st.rerun()

    with col2:
        if st.button("🗑️ 清空", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # 底部信息
    st.markdown("---")
    st.markdown(
        f"<p style='text-align: center; color: gray; font-size: 12px;'>"
        f"TradingAgents Chatbot | {datetime.now().strftime('%Y-%m-%d')}"
        f"</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
