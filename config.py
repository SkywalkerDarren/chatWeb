import json
import os


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
            self.open_ai_chat_model = self.config.get('open_ai_chat_model', 'gpt-3.5-turbo')
            if not self.open_ai_key:
                raise ValueError('open_ai_key is not set')
            self.use_stream = self.config.get('use_stream', False)
            self.use_postgres = self.config.get('use_postgres', False)
            if not self.use_postgres:
                self.index_path = self.config.get('index_path', './temp')
                os.makedirs(self.index_path, exist_ok=True)
            self.postgres_url = self.config.get('postgres_url')
            if self.use_postgres and self.postgres_url is None:
                raise ValueError('postgres_url is not set')
            self.mode = self.config.get('mode', 'console')
            if self.mode not in ['console', 'api']:
                raise ValueError('mode must be console or api')
            self.api_port = self.config.get('api_port', 9531)
            self.api_host = self.config.get('api_host', 'localhost')
