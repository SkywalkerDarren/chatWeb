import numpy as np
import openai
import tiktoken
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import Config, GPTModel, EmbeddingModel


class AI:
    """The AI class."""

    def __init__(self, cfg: Config):
        openai.proxy = cfg.open_ai_proxy
        self._chat_model: GPTModel = cfg.open_ai_chat_model
        self._embedding_model: EmbeddingModel = cfg.open_ai_embedding_model
        self._use_stream = cfg.use_stream
        self._encoding = tiktoken.encoding_for_model(self._chat_model.name)
        self._language = cfg.language
        self._temperature = cfg.temperature
        self.client = OpenAI(api_key=cfg.open_ai_key)

    def _chat_stream(self, messages: list[dict], use_stream: bool = None) -> str:
        use_stream = use_stream if use_stream is not None else self._use_stream
        response = self.client.chat.completions.create(
            n=1,
            temperature=self._temperature,
            stream=use_stream,
            model=self._chat_model.name,
            messages=messages,
        )
        if use_stream:
            data = ""
            for chunk in response:
                if chunk.choices[0].delta.get('content', None) is not None:
                    data += chunk.choices[0].delta.content
                    print(chunk.choices[0].delta.content, end='')
            print()
            return data.strip()
        else:
            print(response.choices[0].message.content.strip())
            input_cost = response.usage.prompt_tokens / 1000 * self._chat_model.input_price_per_k
            output_cost = response.usage.completion_tokens / 1000 * self._chat_model.output_price_per_k
            print(f"Total tokens: {response.usage.total_tokens}, cost: ${input_cost + output_cost}")
            print(f"Input tokens: {response.usage.prompt_tokens}, cost: ${input_cost}")
            print(f"Output tokens: {response.usage.completion_tokens}, cost: ${output_cost}")
            return response.choices[0].message.content.strip()

    def _num_tokens_from_string(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        num_tokens = len(self._encoding.encode(string))
        return num_tokens

    def completion(self, query: str, context: list[str]):
        """Create a completion."""
        context = self._cut_texts(context)
        print(f"Number of query fragments:{len(context)}")

        text = "\n".join(f"{index}. {text}" for index, text in enumerate(context))
        result = self._chat_stream([
            {'role': 'system',
             'content': f'You are a helpful AI article assistant. '
                        f'The following are the relevant article content fragments found from the article. '
                        f'The relevance is sorted from high to low. '
                        f'You can only answer according to the following content:\n```\n{text}\n```\n'
                        f'You need to carefully consider your answer to ensure that it is based on the context. '
                        f'If the context does not mention the content or it is uncertain whether it is correct, '
                        f'please answer "Current context cannot provide effective information."'
                        f'You must use {self._language} to respond.'},
            {'role': 'user', 'content': query},
        ])
        return result

    def _cut_texts(self, context):
        maximum = self._chat_model.context_window - 1024
        for index, text in enumerate(context):
            maximum -= self._num_tokens_from_string(text)
            if maximum < 0:
                context = context[:index + 1]
                print(f"Exceeded maximum length, cut the first {index + 1} fragments")
                break
        return context

    def get_keywords(self, query: str) -> str:
        """Get keywords from the query."""
        result = self._chat_stream([
            {'role': 'user',
             'content': f'You need to extract keywords from the statement or question and '
                        f'return a series of keywords separated by commas.\ncontent: {query}\nkeywords: '},
        ], use_stream=False)
        return result

    def _wrap_create_embedding(self, data):
        if self._embedding_model.name != 'text-embedding-ada-002':
            embedding = self.client.embeddings.create(
                model=self._embedding_model.name,
                input=data,
                dimensions=1536,
            )
        else:
            # text-embedding-ada-002 does not support the dimensions parameter
            embedding = self.client.embeddings.create(
                model=self._embedding_model.name,
                input=data,
            )
        return embedding

    def create_embedding(self, text: str) -> (str, list[float]):
        """Create an embedding for the provided text."""
        embedding = self._wrap_create_embedding(text)
        return text, embedding.data[0].embedding

    def create_embeddings(self, texts: list[str]) -> (list[tuple[str, list[float]]], int):
        """Create embeddings for the provided input."""
        result = []
        query_len = 0
        start_index = 0
        tokens = 0

        def get_embedding(input_slice: list[str]):
            embedding = self._wrap_create_embedding(input_slice)
            return [(txt, data.embedding) for txt, data in
                    zip(input_slice, embedding.data)], embedding.usage.total_tokens

        for index, text in enumerate(texts):
            query_len += self._num_tokens_from_string(text)
            if query_len > self._embedding_model.max_tokens - 1024:
                ebd, tk = get_embedding(texts[start_index:index + 1])
                print(f"Query fragments used tokens: {tk}, cost: ${tk / 1000 * self._embedding_model.price_per_k}")
                query_len = 0
                start_index = index + 1
                tokens += tk
                result.extend(ebd)

        if query_len > 0:
            ebd, tk = get_embedding(texts[start_index:])
            print(f"Query fragments used tokens: {tk}, cost: ${tk / 1000 * self._embedding_model.price_per_k}")
            tokens += tk
            result.extend(ebd)
        return result, tokens

    def generate_summary(self, embeddings, num_candidates=3, use_sif=False):
        """Generate a summary for the provided embeddings."""
        avg_func = self._calc_paragraph_avg_embedding_with_sif if use_sif else self._calc_avg_embedding
        avg_embedding = np.array(avg_func(embeddings))

        paragraphs = [e[0] for e in embeddings]
        embeddings = np.array([e[1] for e in embeddings])
        # 计算每个段落与整个文本的相似度分数
        # Calculate the similarity score between each paragraph and the entire text.
        similarity_scores = cosine_similarity(embeddings, avg_embedding.reshape(1, -1)).flatten()

        # 选择具有最高相似度分数的段落作为摘要的候选段落
        # Select the paragraph with the highest similarity score as the candidate paragraph for the summary.
        candidate_indices = np.argsort(similarity_scores)[::-1][:num_candidates]
        candidate_paragraphs = [f"paragraph {i}: {paragraphs[i]}" for i in candidate_indices]

        print("Calculation completed, start generating summary")

        candidate_paragraphs = self._cut_texts(candidate_paragraphs)

        text = "\n".join(f"{index}. {text}" for index, text in enumerate(candidate_paragraphs))
        result = self._chat_stream([
            {'role': 'system',
             'content': f'As a helpful AI article assistant, '
                        f'I have retrieved the following relevant text fragments from the article, '
                        f'sorted by relevance from high to low. '
                        f'You need to summarize the entire article from these fragments, '
                        f'and present the final result in {self._language}:\n\n{text}\n\n{self._language} summary:'},
        ])
        return result

    @staticmethod
    def _calc_avg_embedding(embeddings) -> list[float]:
        # Calculate the average embedding for the entire text.
        avg_embedding = np.zeros(len(embeddings[0][1]))
        for emb in embeddings:
            avg_embedding += np.array(emb[1])
        avg_embedding /= len(embeddings)
        return avg_embedding.tolist()

    @staticmethod
    def _calc_paragraph_avg_embedding_with_sif(paragraph_list) -> list[float]:
        # calculate the SIF embedding for the entire text
        alpha = 0.001
        # calculate the total number of sentences
        n_sentences = len(paragraph_list)

        # calculate the total number of dimensions in the embeddings
        n_dims = len(paragraph_list[0][1])

        # calculate the IDF values for each word in the sentences
        vectorizer = TfidfVectorizer(use_idf=True)
        vectorizer.fit_transform([paragraph for paragraph, _ in paragraph_list])
        idf = vectorizer.idf_

        # calculate the SIF weights for each sentence
        weights = np.zeros((n_sentences, n_dims))
        for i, (sentence, embedding) in enumerate(paragraph_list):
            sentence_words = sentence.split()
            for word in sentence_words:
                try:
                    word_index = vectorizer.vocabulary_[word]
                    word_idf = idf[word_index]
                    word_weight = alpha / (alpha + word_idf)
                    weights[i] += word_weight * (np.array(embedding) / np.max(embedding))
                except KeyError:
                    pass

        # calculate the weighted average of the sentence embeddings
        weights_sum = np.sum(weights, axis=0)
        weights_sum /= n_sentences
        avg_embedding = np.zeros(n_dims)
        for i, (sentence, embedding) in enumerate(paragraph_list):
            avg_embedding += (np.array(embedding) / np.max(embedding)) - weights[i]
        avg_embedding /= n_sentences

        return avg_embedding.tolist()
