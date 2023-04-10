import json
import os


class Config:
    def __init__(self):
        with open('config.json', 'r') as f:
            self.config = json.load(f)
            self.open_ai_key = self.config.get('open_ai_key')
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
