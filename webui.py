import gradio as gr
import xxhash
from gradio.components import _Keywords

from ai import AI
from config import Config
from contents import *
from storage import Storage


def webui(cfg: Config):
    """Run the web UI."""
    Webui(cfg).run()


class Webui:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.ai = AI(cfg)
        self.hash_id = None

    def _save_to_storage(self, contents, hash_id):
        self.storage = Storage.create_storage(self.cfg)
        if self.storage.been_indexed(hash_id):
            return 0
        else:
            embeddings, tokens = self.ai.create_embeddings(contents)
            self.storage.add_all(embeddings, hash_id)
            return tokens

    def _get_hash_id(self, contents):
        return xxhash.xxh3_128_hexdigest('\n'.join(contents))

    def run(self):
        with gr.Blocks() as demo:

            init_page = gr.Column()
            chat_page = gr.Column(visible=False)

            with init_page:
                with gr.Tab("url"):
                    url_error_box = gr.Textbox(label="Input Error", visible=False)
                    url_box = gr.Textbox(label="URL")
                    url_submit_btn = gr.Button("Submit url")

                    def submit(url):
                        if len(url) == 0:
                            return {url_error_box: gr.update(value="Enter URL", visible=True)}
                        try:
                            print(f"Crawling URL {url}")
                            content, lang = web_crawler_newspaper(url)
                            if len(content) == 0:
                                return {url_error_box: gr.update(value="Can not crawl this url", visible=True)}
                            self.hash_id = self._get_hash_id(content)
                            self._save_to_storage(content, self.hash_id)
                        except Exception as e:
                            return {url_error_box: gr.update(value=str(e), visible=True)}
                        return {
                            url_error_box: gr.update(visible=False),
                            url_box: gr.update(value=""),
                            init_page: gr.update(visible=False),
                            chat_page: gr.update(visible=True),
                        }

                    url_submit_btn.click(
                        submit,
                        [url_box],
                        [init_page, url_error_box, chat_page, url_box],
                    )

                with gr.Tab("file"):
                    file_error_box = gr.Textbox(label="Input Error", visible=False)
                    file_box = gr.File(label="File", file_types=["pdf", "txt", "docx"])
                    file_submit_btn = gr.Button("Submit file")

                    def submit(file):
                        url = file.name
                        if url.endswith('.pdf'):
                            contents, lang = extract_text_from_pdf(url)
                        elif url.endswith('.txt'):
                            contents, lang = extract_text_from_txt(url)
                        elif url.endswith('.docx'):
                            contents, lang = extract_text_from_docx(url)
                        else:
                            return {file_error_box: gr.update(value="Can not read this file", visible=True)}

                        if len(contents) == 0:
                            return {file_error_box: gr.update(value="Empty file", visible=True)}
                        self.hash_id = self._get_hash_id(contents)
                        self._save_to_storage(contents, self.hash_id)

                        return {
                            init_page: gr.update(visible=False),
                            chat_page: gr.update(visible=True),
                            file_box: gr.update(value=_Keywords.NO_VALUE),
                            file_error_box: gr.update(visible=False),
                        }

                    file_submit_btn.click(
                        submit,
                        [file_box],
                        [init_page, chat_page, file_box, file_error_box],
                    )

            with chat_page:
                chatbot = gr.Chatbot()
                msg = gr.Textbox(label="Query")
                reset_box = gr.Button("Reset")

                def respond(message, chat_history):
                    kw = self.ai.get_keywords(message)
                    if len(kw) == 0 or self.hash_id is None:
                        return "", chat_history
                    _, kw_ebd = self.ai.create_embedding(kw)
                    ctx = self.storage.get_texts(kw_ebd, self.hash_id)
                    bot_message = self.ai.completion(message, ctx)
                    chat_history.append((message, bot_message))
                    return "", chat_history

                def reset():
                    self.hash_id = None
                    return {
                        init_page: gr.update(visible=True),
                        chat_page: gr.update(visible=False),
                        chatbot: gr.update(value=[]),
                        msg: gr.update(value=""),
                    }

                msg.submit(respond, [msg, chatbot], [msg, chatbot])
                reset_box.click(reset, None, [init_page, chat_page, chatbot, msg], queue=False)
        demo.launch(server_port=self.cfg.webui_port)
