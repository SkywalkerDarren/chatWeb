import dataclasses
import json
import os


@dataclasses.dataclass
class GPTModel:
    name: str
    context_window: int
    input_price_per_k: float
    output_price_per_k: float


SUPPORTED_GPT_MODELS = [
    GPTModel('gpt-4-turbo-preview', 128_000, 0.01, 0.03),  # gpt-4-0125-preview
    GPTModel('gpt-4-0125-preview', 128_000, 0.01, 0.03),
    GPTModel('gpt-4-1106-preview', 128_000, 0.01, 0.03),

    GPTModel('gpt-4-vision-preview', 128_000, 0.01, 0.03),  # gpt-4-1106-vision-preview
    GPTModel('gpt-4-1106-vision-preview', 128_000, 0.01, 0.03),

    GPTModel('gpt-4', 8192, 0.03, 0.06),  # gpt-4-0613
    GPTModel('gpt-4-0613', 8192, 0.03, 0.06),

    GPTModel('gpt-4-32k', 32768, 0.06, 0.12),  # gpt-4-32k-0613
    GPTModel('gpt-4-32k-0613', 32768, 0.06, 0.12),

    GPTModel('gpt-3.5-turbo', 4096, 0.0005, 0.0015),  # gpt-3.5-turbo-0613
    GPTModel('gpt-3.5-turbo-0125', 16385, 0.0005, 0.0015),
    GPTModel('gpt-3.5-turbo-1106', 16385, 0.0005, 0.0015),
    GPTModel('gpt-3.5-turbo-0613', 4096, 0.0005, 0.0015),

    GPTModel('gpt-3.5-turbo-16k', 16385, 0.0005, 0.0015),  # gpt-3.5-turbo-16k-0613
    GPTModel('gpt-3.5-turbo-16k-0613', 16385, 0.0005, 0.0015),
]


@dataclasses.dataclass
class EmbeddingModel:
    name: str
    price_per_k: float
    max_tokens: int
    dimensions: int


SUPPORTED_EMBEDDING_MODELS = [
    EmbeddingModel('text-embedding-3-small', 0.00002, 8191, 1536),
    EmbeddingModel('text-embedding-3-large', 0.00013, 8191, 1536),
    EmbeddingModel('text-embedding-ada-002', 0.0001, 8191, 1536),
]


class Config:
    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f'config.json not found at {config_path}, '
                                    f'please copy config.example.json to config.json and modify it.')
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            self.language = self.config.get('language', 'Chinese')
            self.open_ai_key = self.config.get('open_ai_key')
            self.open_ai_proxy = self.config.get('open_ai_proxy')
            gpt_model = self.config.get('open_ai_chat_model', 'gpt-3.5-turbo')
            self.open_ai_chat_model = self.get_gpt_model(gpt_model)
            embedding_model = self.config.get('open_ai_embedding_model', 'text-embedding-ada-002')
            self.open_ai_embedding_model = self.get_embedding_model(embedding_model)
            if not self.open_ai_key:
                raise ValueError('open_ai_key is not set')
            self.temperature = self.config.get('temperature', 0.1)
            if self.temperature < 0 or self.temperature > 1:
                raise ValueError(
                    'temperature must be between 0 and 1, less is more conservative, more is more creative')
            self.use_stream = self.config.get('use_stream', False)
            self.use_postgres = self.config.get('use_postgres', False)
            if not self.use_postgres:
                self.index_path = self.config.get('index_path', './temp')
                os.makedirs(self.index_path, exist_ok=True)
            self.postgres_url = self.config.get('postgres_url')
            if self.use_postgres and self.postgres_url is None:
                raise ValueError('postgres_url is not set')
            self.mode = self.config.get('mode', 'webui')
            if self.mode not in ['console', 'api', 'webui']:
                raise ValueError('mode must be console or api or webui')
            self.api_port = self.config.get('api_port', 9531)
            self.api_host = self.config.get('api_host', 'localhost')
            self.webui_port = self.config.get('webui_port', 7860)
            self.webui_host = self.config.get('webui_host', '0.0.0.0')

    def get_gpt_model(self, model: str):
        name_list = [m.name for m in SUPPORTED_GPT_MODELS]
        if model not in name_list:
            raise ValueError('open_ai_chat_model must be one of ' + ', '.join(name_list))
        return next(m for m in SUPPORTED_GPT_MODELS if m.name == model)

    def get_embedding_model(self, model: str):
        name_list = [m.name for m in SUPPORTED_EMBEDDING_MODELS]
        if model not in name_list:
            raise ValueError('open_ai_embedding_model must be one of ' + ', '.join(name_list))
        return next(m for m in SUPPORTED_EMBEDDING_MODELS if m.name == model)
