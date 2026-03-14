import openai
import json
import asyncio
import concurrent.futures
from db.pinecone_db import PineconeDB
from infra.logger import logger
from typing import Dict, Any, List

class QueryService:
    def __init__(
            self, 
            vector_db: PineconeDB = None,
            embedding_function = None
            ):
        
        # Disable reranking for speed (saves 4-8 seconds per query)
        # try:
        #     from FlagEmbedding import FlagReranker
        #     self.reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)
        #     self.use_reranker = True
        # except ImportError as e:
        #     logger.warning(f"FlagReranker not available ({e}), disabling reranking")
        #     self.reranker = None
        #     self.use_reranker = False
    
        self.reranker = None
        self.use_reranker = False
        
        self.vector_db = vector_db
        self.embedding_function = embedding_function

    def _hyde(self, input_query: str) -> str:
        """
        Generates a Hypothetical Document Embedding on query passed
        through the use of GPT-4o.

        Args:
            input_query (str): Query string to be processed.

        Returns:
            str: HyDE result from the input query given.
        """

        instruction = """
            Make an extremely short Hypothetical Document Embedding from the given query (DON'T ANSWER).
        """

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": input_query}
            ],
            max_tokens=16
        )

        return response.choices[0].message.content
    
    def _rerank(self, retrieved_contexts: List[str], query: str, top_k: int = 7) -> List[str]:
        """
        Reranks a context based on a query using the FlagReranker model.

        Args:
            query (str): The query to rerank the context.
            context (str): The context to rerank.

        Returns:
            list: A list of top-k reranked contexts.
        """

        if len(retrieved_contexts) == 0:
            logger.warning("No context retrieved for reranking")
            return []
        elif len(query) == 0:
            logger.warning("No query received for reranking")
            return []

        context_list = [[x, query] for x in retrieved_contexts]

        reranked_contexts = self.reranker.compute_score(context_list)

        # Get top-k indices (highest scores)
        top_indices = sorted(range(len(reranked_contexts)), key=lambda i: reranked_contexts[i])[-top_k:]

        res = []
        for idx in top_indices:
            res.append(context_list[idx][0])

        return res

    
    def query_two_countries(self, query: str, home_country: str, host_country: str, top_k: int = 7, conversation_history: list = None) -> Dict[str, Any]:
        """
        Queries the data based on the query passed for two countries.

        Args:
            query (str): The query to query the data.
            home_country (str): The home country of the data.
            host_country (str): The host country of the data.
            top_k (int): The number of top results to return.

        Returns:
            str: The answer to the query.
        """

        # PERFORMANCE: HyDE disabled to reduce processing time
        # hyde_query = self.hyde(query)
        # logger.debug(f"HyDE query: {hyde_query}")

        # Generate query embedding
        query_embedding = self.embedding_function([query])
        
        def query_country(country):
            return self.vector_db.query(
                query_embeddings=query_embedding,
                n_results=top_k,
                country=country
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            home_future = executor.submit(query_country, home_country)
            host_future = executor.submit(query_country, host_country)
            
            home_country_results = home_future.result()
            host_country_results = host_future.result()

        logger.debug(f"Retrieved {len(home_country_results['documents'][0])} results from Pinecone for home country: {home_country}")
        logger.debug(f"Retrieved {len(host_country_results['documents'][0])} results from Pinecone for host country: {host_country}")

        home_country_contexts = []
        seen_parents = set()

        # Home country contexts
        for i, document in enumerate(home_country_results["documents"][0]):
            metadata = home_country_results["metadatas"][0][i]
            chunk_id = metadata.get("chunk_id", f"chunk_{i}")
            if chunk_id in seen_parents:
                continue
            home_country_contexts.append(document)
            seen_parents.add(chunk_id)

        # try:
        #     reranked_results = self.rerank(home_country_contexts, query, top_k)
        # except Exception as e:
        #     raise ValueError(f"Error reranking contexts: {e}")

        # Use top contexts directly
        reranked_results = home_country_contexts[:top_k] if home_country_contexts else []
        logger.debug(f"Using top {len(reranked_results)} home country contexts (no reranking)")

        try:
            home_country_context = "---".join(reranked_results)
        except:
            logger.warning(f"Empty home country contexts")
            home_country_context = ""

        # Host country contexts
        host_country_contexts = []
        for i, document in enumerate(host_country_results["documents"][0]):
            metadata = host_country_results["metadatas"][0][i]
            chunk_id = metadata.get("chunk_id", f"chunk_{i}")
            if chunk_id in seen_parents:
                continue
            host_country_contexts.append(document)
            seen_parents.add(chunk_id)

        # try:
        #     reranked_results = self.rerank(host_country_contexts, query, top_k)
        # except Exception as e:
        #     raise ValueError(f"Error reranking contexts: {e}")

        # Use top contexts directly
        reranked_results = host_country_contexts[:top_k] if host_country_contexts else []
        logger.debug(f"Using top {len(reranked_results)} host country contexts (no reranking)")

        try:
            host_country_context = "---".join(reranked_results)
        except:
            logger.warning(f"Empty host country contexts")
            host_country_context = ""

        user_prompt = query
        
        system_prompt = f"""
        You are an AI chatbot that helps immigrants make their minds up about political parties in their current country. The context is party platforms for the parties in question. Please be helpful. Be as accurate as possible. Do not include any persuasive arguments for the other side. Your goal is not to convince people of one side or the other. Your goal is to help people make up their minds. Return the information in an accessible reading level (high school). Always end in complete sentences. Use details from conversation history to seem more personable. This chat is for people on the go. Be terse but helpful (2-3 sentences MAX). Pay attention to the query. Always begin by drawing a clear contrast between the parties in question (e.g., The X, Y, and Z parties [specific difference, avoid mealymouthed responses]). Pretend you are a neutral expert having a natural conversation. Your goal is to translate party systems from one country to another. Do your best to provide a guess of how parties in two countries relate. Being too vague will harm the participation of immigrants. Be concrete and take creative liberties in drawing comparisons. Mention multiple parties when necessary and disclose whether they have recently been in the governing coalition. Provide a balanced take and make sure to mention all of the relevant parties. Do not leave parties out. If the user starts talking in a foreign language, follow their lead. Ask follow-up questions to help the participant determine which party in the host country they are closest to. Take it step by step.
        Background: the immigrant is from {home_country} and is now living in {host_country}.
        Home country context: {home_country_context}.
        Host country context: {host_country_context}."""

        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_prompt})

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=350,
            stream=False
        )

        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"question": query, "response": content}

        parsed["home_country_context"] = home_country_context
        parsed["host_country_context"] = host_country_context

        return parsed
    
    # def query_two_countries_stream(self, query: str, home_country: str, host_country: str, top_k: int = 7):
    #     """
    #     Streams the response for two countries query.

    #     Args:
    #         query (str): The query to query the data.
    #         home_country (str): The home country of the data.
    #         host_country (str): The host country of the data.
    #         top_k (int): The number of top results to return.

    #     Yields:
    #         Dict[str, Any]: Streaming chunks of the response.
    #     """

    #     # Get contexts (same as non-streaming version)
    #     # LATENCY OPTIMIZATION 3: Use cached embedding function
    #     query_embedding = self.get_cached_embedding(query)
        
    #     # LATENCY OPTIMIZATION: Parallel Pinecone queries for streaming
    #     def query_country(country):
    #         return self.vector_db.query(
    #             query_embeddings=query_embedding,
    #             n_results=top_k,
    #             country=country
    #         )
        
    #     with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    #         home_future = executor.submit(query_country, home_country)
    #         host_future = executor.submit(query_country, host_country)
            
    #         home_country_results = home_future.result()
    #         host_country_results = host_future.result()

    #     logger.debug(f"Retrieved from Pinecone for both countries")

    #     # Process home country contexts
    #     home_country_contexts = []
    #     seen_chunks = set()

    #     for i, document in enumerate(home_country_results["documents"][0]):
    #         metadata = home_country_results["metadatas"][0][i]
    #         chunk_id = metadata.get("chunk_id", f"chunk_{i}")
    #         if chunk_id in seen_chunks:
    #             continue
    #         home_country_contexts.append(document)
    #         seen_chunks.add(chunk_id)

    #     # PERFORMANCE OPTIMIZATION: Skip reranking for streaming (speed critical)
    #     # try:
    #     #     reranked_results = self.rerank(home_country_contexts, query, top_k)
    #     #     home_country_context = "---".join(reranked_results)
    #     # except:
    #     #     logger.warning(f"Empty reranked results for home country")
    #     #     home_country_context = ""
        
    #     # Use top contexts directly for home country
    #     top_home_contexts = home_country_contexts[:top_k] if home_country_contexts else []
    #     home_country_context = "---".join(top_home_contexts) if top_home_contexts else ""

    #     # Process host country contexts
    #     host_country_contexts = []
    #     for i, document in enumerate(host_country_results["documents"][0]):
    #         metadata = host_country_results["metadatas"][0][i]
    #         chunk_id = metadata.get("chunk_id", f"chunk_{i}")
    #         if chunk_id in seen_chunks:
    #             continue
    #         host_country_contexts.append(document)
    #         seen_chunks.add(chunk_id)

    #     # PERFORMANCE OPTIMIZATION: Skip reranking for host country streaming
    #     # try:
    #     #     reranked_results = self.rerank(host_country_contexts, query, top_k)
    #     #     host_country_context = "---".join(reranked_results)
    #     # except:
    #     #     logger.warning(f"Empty reranked results for host country")
    #     #     host_country_context = ""
        
    #     # Use top contexts directly for host country
    #     top_host_contexts = host_country_contexts[:top_k] if host_country_contexts else []
    #     host_country_context = "---".join(top_host_contexts) if top_host_contexts else ""

    #     user_prompt = f"""
    #         HOME COUNTRY DOCUMENT: {home_country_context}
    #         HOST COUNTRY DOCUMENT: {host_country_context}

    #         QUESTION: {query}
    #         """
        
    #     system_prompt = (
    #         "You are a helpful assistant that can answer questions about the home and host countries."
    #         "Answer the users QUESTION using the DOCUMENT text above."
    #         "Keep your answer ground in the facts of the DOCUMENT."
    #         "Only use relevant information from the DOCUMENT to answer the QUESTION."
    #     )

    #     # PERFORMANCE OPTIMIZATION: Use faster model for streaming
    #     stream = openai.chat.completions.create(
    #         model="gpt-4o-mini",  # Faster and cheaper than gpt-4o
    #         messages=[
    #             {"role": "system", "content": system_prompt},
    #             {"role": "user", "content": user_prompt}
    #         ],
    #         temperature=0.2,
    #         max_tokens=400,  # Limit for speed
    #         stream=True
    #     )

    #     try:
    #         for chunk in stream:
    #             if chunk.choices[0].delta.content is not None:
    #                 yield {
    #                     "type": "chunk",
    #                     "content": chunk.choices[0].delta.content
    #                 }
            
    #         # Send completion signal
    #         yield {
    #             "type": "done",
    #             "home_country_context": home_country_context,
    #             "host_country_context": host_country_context
    #         }
    #     except Exception as e:
    #         logger.error(f"Streaming error: {e}")
    #         yield {
    #             "type": "error",
    #             "error": str(e)
    #         }
    
    # def agentic_query(self, query: str, country: str, top_k: int = 7) -> Dict[str, Any]:
    #     """
    #     Queries the data based on the query passed using an agentic approach.

    #     Args:
    #         query (str): The query to query the data.
    #         country (str): The country of the data.
    #         top_k (int): The number of top results to return.
    #     """

    #     pass