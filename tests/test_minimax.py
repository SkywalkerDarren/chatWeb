"""Tests for MiniMax model support in ChatWeb."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from config import Config, GPTModel, SUPPORTED_GPT_MODELS


class TestMiniMaxModelsInConfig(unittest.TestCase):
    """Unit tests for MiniMax model definitions in config."""

    def test_minimax_m27_in_supported_models(self):
        names = [m.name for m in SUPPORTED_GPT_MODELS]
        self.assertIn('MiniMax-M2.7', names)

    def test_minimax_m27_highspeed_in_supported_models(self):
        names = [m.name for m in SUPPORTED_GPT_MODELS]
        self.assertIn('MiniMax-M2.7-highspeed', names)

    def test_minimax_m27_context_window(self):
        model = next(m for m in SUPPORTED_GPT_MODELS if m.name == 'MiniMax-M2.7')
        self.assertEqual(model.context_window, 1_000_000)

    def test_minimax_m27_highspeed_context_window(self):
        model = next(m for m in SUPPORTED_GPT_MODELS if m.name == 'MiniMax-M2.7-highspeed')
        self.assertEqual(model.context_window, 1_000_000)

    def test_minimax_m27_pricing(self):
        model = next(m for m in SUPPORTED_GPT_MODELS if m.name == 'MiniMax-M2.7')
        self.assertEqual(model.input_price_per_k, 0.004)
        self.assertEqual(model.output_price_per_k, 0.016)

    def test_minimax_m27_highspeed_pricing(self):
        model = next(m for m in SUPPORTED_GPT_MODELS if m.name == 'MiniMax-M2.7-highspeed')
        self.assertEqual(model.input_price_per_k, 0.001)
        self.assertEqual(model.output_price_per_k, 0.004)

    def test_gpt_models_still_present(self):
        """Ensure existing OpenAI models are not broken."""
        names = [m.name for m in SUPPORTED_GPT_MODELS]
        self.assertIn('gpt-3.5-turbo', names)
        self.assertIn('gpt-4', names)
        self.assertIn('gpt-4-turbo-preview', names)


class TestConfigMiniMax(unittest.TestCase):
    """Unit tests for Config class MiniMax support."""

    def _create_config(self, overrides=None):
        config = {
            "open_ai_key": "test-key",
            "open_ai_chat_model": "gpt-3.5-turbo",
            "open_ai_embedding_model": "text-embedding-ada-002",
            "temperature": 0.1,
        }
        if overrides:
            config.update(overrides)
        tmpdir = tempfile.mkdtemp()
        config_path = os.path.join(tmpdir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)
        return tmpdir, config_path

    def test_minimax_model_selection(self):
        tmpdir, _ = self._create_config({"open_ai_chat_model": "MiniMax-M2.7"})
        with patch.object(Config, '__init__', lambda self: None):
            cfg = Config.__new__(Config)
        cfg.config = json.load(open(os.path.join(tmpdir, "config.json")))
        model = cfg.get_gpt_model("MiniMax-M2.7")
        self.assertEqual(model.name, "MiniMax-M2.7")
        self.assertEqual(model.context_window, 1_000_000)

    def test_minimax_highspeed_model_selection(self):
        with patch.object(Config, '__init__', lambda self: None):
            cfg = Config.__new__(Config)
        model = cfg.get_gpt_model("MiniMax-M2.7-highspeed")
        self.assertEqual(model.name, "MiniMax-M2.7-highspeed")

    def test_is_minimax_model_true(self):
        with patch.object(Config, '__init__', lambda self: None):
            cfg = Config.__new__(Config)
        cfg.open_ai_chat_model = GPTModel('MiniMax-M2.7', 1_000_000, 0.004, 0.016)
        self.assertTrue(cfg.is_minimax_model())

    def test_is_minimax_model_false(self):
        with patch.object(Config, '__init__', lambda self: None):
            cfg = Config.__new__(Config)
        cfg.open_ai_chat_model = GPTModel('gpt-4', 8192, 0.03, 0.06)
        self.assertFalse(cfg.is_minimax_model())

    def test_base_url_config(self):
        tmpdir, _ = self._create_config({
            "open_ai_base_url": "https://api.minimax.io/v1",
            "open_ai_chat_model": "MiniMax-M2.7",
        })
        config_path = os.path.join(tmpdir, "config.json")
        # Patch the config path
        with patch('config.os.path.join', return_value=config_path):
            with patch('config.os.path.exists', return_value=True):
                with patch('config.os.path.dirname', return_value=tmpdir):
                    cfg = Config()
        self.assertEqual(cfg.open_ai_base_url, "https://api.minimax.io/v1")

    def test_temperature_clamping_for_minimax(self):
        tmpdir, _ = self._create_config({
            "open_ai_chat_model": "MiniMax-M2.7",
            "temperature": 0,
        })
        config_path = os.path.join(tmpdir, "config.json")
        with patch('config.os.path.join', return_value=config_path):
            with patch('config.os.path.exists', return_value=True):
                with patch('config.os.path.dirname', return_value=tmpdir):
                    cfg = Config()
        self.assertGreater(cfg.temperature, 0)
        self.assertEqual(cfg.temperature, 0.01)

    def test_temperature_not_clamped_for_openai(self):
        tmpdir, _ = self._create_config({
            "open_ai_chat_model": "gpt-3.5-turbo",
            "temperature": 0,
        })
        config_path = os.path.join(tmpdir, "config.json")
        with patch('config.os.path.join', return_value=config_path):
            with patch('config.os.path.exists', return_value=True):
                with patch('config.os.path.dirname', return_value=tmpdir):
                    cfg = Config()
        self.assertEqual(cfg.temperature, 0)

    def test_base_url_defaults_to_none(self):
        tmpdir, _ = self._create_config()
        config_path = os.path.join(tmpdir, "config.json")
        with patch('config.os.path.join', return_value=config_path):
            with patch('config.os.path.exists', return_value=True):
                with patch('config.os.path.dirname', return_value=tmpdir):
                    cfg = Config()
        self.assertIsNone(cfg.open_ai_base_url)


class TestAIMiniMax(unittest.TestCase):
    """Unit tests for AI class MiniMax support."""

    def _make_config(self, model_name='MiniMax-M2.7', base_url='https://api.minimax.io/v1'):
        cfg = MagicMock()
        cfg.open_ai_proxy = None
        cfg.open_ai_key = 'test-key'
        cfg.open_ai_base_url = base_url
        cfg.open_ai_chat_model = GPTModel(model_name, 1_000_000, 0.004, 0.016)
        cfg.open_ai_embedding_model = MagicMock()
        cfg.open_ai_embedding_model.name = 'text-embedding-ada-002'
        cfg.use_stream = False
        cfg.language = 'English'
        cfg.temperature = 0.5
        return cfg

    @patch('ai.OpenAI')
    def test_minimax_creates_client_with_base_url(self, mock_openai):
        from ai import AI
        cfg = self._make_config()
        ai = AI(cfg)
        mock_openai.assert_called_once_with(
            api_key='test-key',
            base_url='https://api.minimax.io/v1',
        )

    @patch('ai.OpenAI')
    def test_openai_creates_client_without_base_url(self, mock_openai):
        from ai import AI
        cfg = self._make_config(model_name='gpt-4', base_url=None)
        cfg.open_ai_chat_model = GPTModel('gpt-4', 8192, 0.03, 0.06)
        ai = AI(cfg)
        mock_openai.assert_called_once_with(api_key='test-key')

    @patch('ai.OpenAI')
    def test_tiktoken_fallback_for_minimax(self, mock_openai):
        from ai import AI
        cfg = self._make_config()
        ai = AI(cfg)
        # Should not raise and should use cl100k_base fallback
        self.assertIsNotNone(ai._encoding)
        tokens = ai._num_tokens_from_string("Hello world")
        self.assertGreater(tokens, 0)

    @patch('ai.OpenAI')
    def test_tiktoken_works_for_openai_model(self, mock_openai):
        from ai import AI
        cfg = self._make_config(model_name='gpt-4', base_url=None)
        cfg.open_ai_chat_model = GPTModel('gpt-4', 8192, 0.03, 0.06)
        ai = AI(cfg)
        self.assertIsNotNone(ai._encoding)


class TestConfigExampleJson(unittest.TestCase):
    """Test that config.example.json includes base_url field."""

    def test_config_example_has_base_url(self):
        example_path = os.path.join(os.path.dirname(__file__), '..', 'config.example.json')
        with open(example_path) as f:
            config = json.load(f)
        self.assertIn('open_ai_base_url', config)


class TestMiniMaxIntegration(unittest.TestCase):
    """Integration tests for MiniMax — require MINIMAX_API_KEY env var."""

    def setUp(self):
        self.api_key = os.environ.get('MINIMAX_API_KEY')
        if not self.api_key:
            self.skipTest('MINIMAX_API_KEY not set')

    @patch('ai.OpenAI')
    def test_minimax_chat_completion_mock(self, mock_openai_cls):
        """Integration-style test with mocked OpenAI client."""
        from ai import AI

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test answer"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_client.chat.completions.create.return_value = mock_response

        cfg = MagicMock()
        cfg.open_ai_proxy = None
        cfg.open_ai_key = self.api_key
        cfg.open_ai_base_url = 'https://api.minimax.io/v1'
        cfg.open_ai_chat_model = GPTModel('MiniMax-M2.7', 1_000_000, 0.004, 0.016)
        cfg.open_ai_embedding_model = MagicMock()
        cfg.open_ai_embedding_model.name = 'text-embedding-ada-002'
        cfg.use_stream = False
        cfg.language = 'English'
        cfg.temperature = 0.5

        ai = AI(cfg)
        result = ai.completion("What is AI?", ["AI is artificial intelligence."])
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

        # Verify the call used the MiniMax model
        call_args = mock_client.chat.completions.create.call_args
        self.assertEqual(call_args.kwargs['model'], 'MiniMax-M2.7')

    def test_minimax_live_chat(self):
        """Live integration test — calls real MiniMax API."""
        from ai import AI

        cfg = MagicMock()
        cfg.open_ai_proxy = None
        cfg.open_ai_key = self.api_key
        cfg.open_ai_base_url = 'https://api.minimax.io/v1'
        cfg.open_ai_chat_model = GPTModel('MiniMax-M2.7', 1_000_000, 0.004, 0.016)
        cfg.open_ai_embedding_model = MagicMock()
        cfg.open_ai_embedding_model.name = 'text-embedding-ada-002'
        cfg.use_stream = False
        cfg.language = 'English'
        cfg.temperature = 0.5

        ai = AI(cfg)
        result = ai.completion("What is 2+2?", ["Basic math: 2+2=4"])
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_minimax_live_stream(self):
        """Live integration test with streaming enabled."""
        from ai import AI

        cfg = MagicMock()
        cfg.open_ai_proxy = None
        cfg.open_ai_key = self.api_key
        cfg.open_ai_base_url = 'https://api.minimax.io/v1'
        cfg.open_ai_chat_model = GPTModel('MiniMax-M2.7-highspeed', 1_000_000, 0.001, 0.004)
        cfg.open_ai_embedding_model = MagicMock()
        cfg.open_ai_embedding_model.name = 'text-embedding-ada-002'
        cfg.use_stream = True
        cfg.language = 'English'
        cfg.temperature = 0.5

        ai = AI(cfg)
        result = ai.completion("Say hello", ["Greeting: Hello!"])
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


if __name__ == '__main__':
    unittest.main()
