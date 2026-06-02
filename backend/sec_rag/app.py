import gradio as gr
from dotenv import load_dotenv

from implementation.answer import answer_question

load_dotenv(override=True)


def format_context(context):
    result = "<h2 style='color: #ff7800;'>Relevant Context</h2>\n\n"
    for doc in context:
        result += f"<span style='color: #ff7800;'>Source: {doc.metadata['source']}</span>\n\n"
        result += doc.page_content + "\n\n"
    return result


def chat(history):
    last_message = history[-1]["content"]
    if isinstance(last_message, list):
        last_message = " ".join(
            block.get("text", "") for block in last_message if block.get("type") == "text"
        )
    prior = history[:-1]
    try:
        answer, context = answer_question(last_message, prior)
    except Exception as e:
        import traceback
        traceback.print_exc()  # prints the real error to terminal
        error_msg = f"Error: {type(e).__name__}: {e}"
        history.append({"role": "assistant", "content": error_msg})
        return history, f"<pre>{error_msg}</pre>"
    history.append({"role": "assistant", "content": answer})
    return history, format_context(context)

def main():
    def put_message_in_chatbot(message, history):
        return "", history + [{"role": "user", "content": message}]

    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    with gr.Blocks(title="Alex SEC 10-K Assistant") as ui:
        gr.Markdown(
            "# Alex SEC 10-K RAG\n"
            "Ask questions about S&P 500 company filings in the knowledge base."
        )

        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    label="💬 Conversation", height=600
                )
                message = gr.Textbox(
                    label="Your Question",
                    placeholder="Ask anything about Insurellm...",
                    show_label=False,
                )

            with gr.Column(scale=1):
                context_markdown = gr.Markdown(
                    label="📚 Retrieved Context",
                    value="*Retrieved context will appear here*",
                    container=True,
                    height=600,
                )

        message.submit(
            put_message_in_chatbot, inputs=[message, chatbot], outputs=[message, chatbot]
        ).then(chat, inputs=chatbot, outputs=[chatbot, context_markdown])

    ui.launch(inbrowser=True, theme=theme)


if __name__ == "__main__":
    main()
