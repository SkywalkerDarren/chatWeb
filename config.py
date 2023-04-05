import json


class Config:
    def __init__(self):
        with open('config.json', 'r') as f:
            self.config = json.load(f)
            self.open_ai_key = self.config.get('open_ai_key')
            if not self.open_ai_key:
                raise ValueError('open_ai_key is not set')
            self.use_stream = self.config.get('use_stream', False)
            self.use_postgres = self.config.get('use_postgres', False)
            self.postgres_url = self.config.get('postgres_url')
            if self.use_postgres and self.postgres_url is None:
                raise ValueError('postgres_url is not set')
