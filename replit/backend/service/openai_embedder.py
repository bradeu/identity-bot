import openai
from typing import List

Documents = List[str]
Embeddings = List[List[float]]


class OpenAIEmbeddingFunction:
    def __init__(self, api_key: str, model_name: str = "text-embedding-ada-002"):
        """
        Initialize OpenAI embedding function.

        Args:
            api_key: OpenAI API key (required)
            model_name: OpenAI embedding model to use
        """
        if not api_key:
            raise ValueError("OpenAI API key is required.")

        self.api_key = api_key
        self.model_name = model_name

        # Set OpenAI API key
        openai.api_key = self.api_key

    def __call__(self, input: Documents) -> Embeddings:
        """
        Generate embeddings using OpenAI API.

        Args:
            input (Documents): The text to embed.

        Returns:
            Embeddings: The embeddings of the text.
        """
        try:
            # Handle both single string and list of strings
            texts = input if isinstance(input, list) else [input]

            response = openai.embeddings.create(
                input=texts,
                model=self.model_name
            )

            # Extract embeddings from response
            embeddings = [data.embedding for data in response.data]

            # Return as list (not numpy array) for Pinecone compatibility
            return embeddings

        except Exception as e:
            print(f"OpenAI embedding error: {e}")
            raise
