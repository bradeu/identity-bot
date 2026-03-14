import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from service.query import QueryService


class TestQueryService:
    
    @pytest.fixture
    def mock_chroma_db(self):
        return Mock()
    
    @pytest.fixture
    def query_service_with_reranker(self, mock_chroma_db):
        with patch('service.query.FlagReranker') as mock_reranker_class:
            mock_reranker = Mock()
            mock_reranker_class.return_value = mock_reranker
            
            service = QueryService(chroma_db=mock_chroma_db)
            service.reranker = mock_reranker
            service.use_reranker = True
            return service
    
    @pytest.fixture
    def query_service_without_reranker(self, mock_chroma_db):
        with patch('service.query.FlagReranker', side_effect=ImportError("FlagReranker not available")):
            service = QueryService(chroma_db=mock_chroma_db)
            return service
    
    def test_init_with_reranker_success(self, mock_chroma_db):
        with patch('service.query.FlagReranker') as mock_reranker_class:
            mock_reranker = Mock()
            mock_reranker_class.return_value = mock_reranker
            
            service = QueryService(chroma_db=mock_chroma_db)
            
            assert service.chroma_db == mock_chroma_db
            assert service.reranker == mock_reranker
            assert service.use_reranker is True
            mock_reranker_class.assert_called_once_with('BAAI/bge-reranker-v2-m3', use_fp16=True)
    
    def test_init_with_reranker_import_error(self, mock_chroma_db):
        with patch('service.query.FlagReranker', side_effect=ImportError("Module not found")):
            service = QueryService(chroma_db=mock_chroma_db)
            
            assert service.chroma_db == mock_chroma_db
            assert service.reranker is None
            assert service.use_reranker is False
    
    def test_init_without_chroma_db(self):
        with patch('service.query.FlagReranker') as mock_reranker_class:
            service = QueryService()
            
            assert service.chroma_db is None
            assert service.use_reranker is True
    
    @patch('service.query.openai.chat.completions.create')
    def test_hyde_success(self, mock_openai, query_service_with_reranker):
        # Setup
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "hypothetical document content"
        mock_openai.return_value = mock_response
        
        input_query = "What is the party's stance on healthcare?"
        
        # Execute
        result = query_service_with_reranker.hyde(input_query)
        
        # Verify
        assert result == "hypothetical document content"
        mock_openai.assert_called_once()
        
        # Verify call structure
        call_args = mock_openai.call_args
        assert call_args[1]['model'] == 'gpt-4o'
        assert call_args[1]['max_tokens'] == 16
        assert len(call_args[1]['messages']) == 2
        assert call_args[1]['messages'][0]['role'] == 'system'
        assert call_args[1]['messages'][1]['role'] == 'user'
        assert call_args[1]['messages'][1]['content'] == input_query
    
    @patch('service.query.openai.chat.completions.create')
    def test_hyde_openai_error(self, mock_openai, query_service_with_reranker):
        # Setup
        mock_openai.side_effect = Exception("OpenAI API error")
        
        # Execute & Verify
        with pytest.raises(Exception, match="OpenAI API error"):
            query_service_with_reranker.hyde("test query")
    
    def test_rerank_success(self, query_service_with_reranker):
        # Setup
        retrieved_contexts = [
            "Context about healthcare policy",
            "Context about education funding", 
            "Context about environmental protection"
        ]
        query = "healthcare policy"
        query_service_with_reranker.reranker.compute_score.return_value = [0.1, 0.8, 0.3]
        
        # Execute
        result = query_service_with_reranker.rerank(retrieved_contexts, query, top_k=2)
        
        # Verify
        assert len(result) == 2
        # Should return contexts with highest scores (0.8 and 0.3)
        assert "Context about education funding" in result
        assert "Context about environmental protection" in result
        
        # Verify reranker was called correctly
        expected_context_list = [
            ["Context about healthcare policy", "healthcare policy"],
            ["Context about education funding", "healthcare policy"],
            ["Context about environmental protection", "healthcare policy"]
        ]
        query_service_with_reranker.reranker.compute_score.assert_called_once_with(expected_context_list)
    
    def test_rerank_empty_contexts(self, query_service_with_reranker):
        # Setup
        retrieved_contexts = []
        query = "test query"
        
        # Execute & Verify
        result = query_service_with_reranker.rerank(retrieved_contexts, query)
        assert isinstance(result, ValueError)
    
    def test_rerank_empty_query(self, query_service_with_reranker):
        # Setup
        retrieved_contexts = ["some context"]
        query = ""
        
        # Execute & Verify
        result = query_service_with_reranker.rerank(retrieved_contexts, query)
        assert isinstance(result, ValueError)
    
    def test_rerank_top_k_larger_than_contexts(self, query_service_with_reranker):
        # Setup
        retrieved_contexts = ["Context 1", "Context 2"]
        query = "test query"
        query_service_with_reranker.reranker.compute_score.return_value = [0.5, 0.7]
        
        # Execute
        result = query_service_with_reranker.rerank(retrieved_contexts, query, top_k=5)
        
        # Verify - should return all available contexts
        assert len(result) == 2
        assert "Context 2" in result  # Higher score
        assert "Context 1" in result
    
    @patch('service.query.get_collection_from_country')
    @patch('service.query.openai.chat.completions.create')
    def test_query_success(self, mock_openai, mock_get_collection, query_service_with_reranker):
        # Setup
        # Mock HyDE response
        mock_hyde_response = Mock()
        mock_hyde_response.choices = [Mock()]
        mock_hyde_response.choices[0].message.content = "hyde query"
        
        # Mock final response
        mock_final_response = Mock()
        mock_final_response.choices = [Mock()]
        mock_final_response.choices[0].message.content = '{"answer": "Healthcare policy details", "confidence": "high"}'
        
        mock_openai.side_effect = [mock_hyde_response, mock_final_response]
        
        # Mock ChromaDB response
        query_service_with_reranker.chroma_db.query.return_value = {
            "metadatas": [[
                {"parent_id": "parent_1"},
                {"parent_id": "parent_2"},
                {"parent_id": "parent_1"}  # Duplicate
            ]]
        }
        
        # Mock MongoDB collection
        mock_collection = Mock()
        mock_collection.find_one.side_effect = [
            {"parent_chunk": "Healthcare policy chunk 1"},
            {"parent_chunk": "Healthcare policy chunk 2"}
        ]
        mock_get_collection.return_value = mock_collection
        
        # Mock reranker
        query_service_with_reranker.reranker.compute_score.return_value = [0.8, 0.6]
        
        query = "What is the healthcare policy?"
        country = "Canada"
        
        # Execute
        result = query_service_with_reranker.query(query, country, top_k=2)
        
        # Verify
        assert result["answer"] == "Healthcare policy details"
        assert result["confidence"] == "high"
        assert "context" in result
        
        # Verify ChromaDB was queried
        query_service_with_reranker.chroma_db.query.assert_called_once_with(
            query_texts=["hyde query"],
            n_results=30,
            country=country
        )
        
        # Verify MongoDB was queried for unique parent chunks
        assert mock_collection.find_one.call_count == 2
    
    @patch('service.query.get_collection_from_country')
    @patch('service.query.openai.chat.completions.create')
    def test_query_json_decode_error(self, mock_openai, mock_get_collection, query_service_with_reranker):
        # Setup
        mock_hyde_response = Mock()
        mock_hyde_response.choices = [Mock()]
        mock_hyde_response.choices[0].message.content = "hyde query"
        
        mock_final_response = Mock()
        mock_final_response.choices = [Mock()]
        mock_final_response.choices[0].message.content = "Invalid JSON response"
        
        mock_openai.side_effect = [mock_hyde_response, mock_final_response]
        
        # Mock other dependencies
        query_service_with_reranker.chroma_db.query.return_value = {
            "metadatas": [[{"parent_id": "parent_1"}]]
        }
        
        mock_collection = Mock()
        mock_collection.find_one.return_value = {"parent_chunk": "Test chunk"}
        mock_get_collection.return_value = mock_collection
        
        query_service_with_reranker.reranker.compute_score.return_value = [0.8]
        
        # Execute
        result = query_service_with_reranker.query("test query", "Canada")
        
        # Verify fallback JSON structure
        assert result["question"] == "test query"
        assert result["raw_response"] == "Invalid JSON response"
        assert "context" in result
    
    @patch('service.query.get_collection_from_country')
    @patch('service.query.openai.chat.completions.create')
    def test_query_rerank_error(self, mock_openai, mock_get_collection, query_service_with_reranker):
        # Setup
        mock_hyde_response = Mock()
        mock_hyde_response.choices = [Mock()]
        mock_hyde_response.choices[0].message.content = "hyde query"
        
        mock_openai.return_value = mock_hyde_response
        
        query_service_with_reranker.chroma_db.query.return_value = {
            "metadatas": [[{"parent_id": "parent_1"}]]
        }
        
        mock_collection = Mock()
        mock_collection.find_one.return_value = {"parent_chunk": "Test chunk"}
        mock_get_collection.return_value = mock_collection
        
        # Mock reranker to raise error
        query_service_with_reranker.reranker.compute_score.side_effect = Exception("Reranking failed")
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Error reranking contexts: Reranking failed"):
            query_service_with_reranker.query("test query", "Canada")
    
    @patch('service.query.get_collection_from_country')
    @patch('service.query.openai.chat.completions.create')
    def test_query_chroma_db_error(self, mock_openai, mock_get_collection, query_service_with_reranker):
        # Setup
        mock_hyde_response = Mock()
        mock_hyde_response.choices = [Mock()]
        mock_hyde_response.choices[0].message.content = "hyde query"
        mock_openai.return_value = mock_hyde_response
        
        query_service_with_reranker.chroma_db.query.side_effect = Exception("ChromaDB query failed")
        
        # Execute & Verify
        with pytest.raises(Exception, match="ChromaDB query failed"):
            query_service_with_reranker.query("test query", "Canada")
    
    @patch('service.query.get_collection_from_country')
    @patch('service.query.openai.chat.completions.create')
    def test_query_deduplicate_parent_chunks(self, mock_openai, mock_get_collection, query_service_with_reranker):
        # Setup
        mock_hyde_response = Mock()
        mock_hyde_response.choices = [Mock()]
        mock_hyde_response.choices[0].message.content = "hyde query"
        
        mock_final_response = Mock()
        mock_final_response.choices = [Mock()]
        mock_final_response.choices[0].message.content = '{"answer": "test"}'
        
        mock_openai.side_effect = [mock_hyde_response, mock_final_response]
        
        # ChromaDB returns child chunks with same parent_id
        query_service_with_reranker.chroma_db.query.return_value = {
            "metadatas": [[
                {"parent_id": "parent_1"},
                {"parent_id": "parent_1"},  # Duplicate
                {"parent_id": "parent_2"},
                {"parent_id": "parent_1"}   # Another duplicate
            ]]
        }
        
        mock_collection = Mock()
        mock_collection.find_one.side_effect = [
            {"parent_chunk": "Chunk 1"},
            {"parent_chunk": "Chunk 2"}
        ]
        mock_get_collection.return_value = mock_collection
        
        query_service_with_reranker.reranker.compute_score.return_value = [0.8, 0.6]
        
        # Execute
        query_service_with_reranker.query("test query", "Canada")
        
        # Verify - should only fetch unique parent chunks
        assert mock_collection.find_one.call_count == 2
        mock_collection.find_one.assert_any_call({"parent_id": "parent_1"})
        mock_collection.find_one.assert_any_call({"parent_id": "parent_2"})
    
    @patch('service.query.openai.chat.completions.create')
    def test_query_system_prompt_content(self, mock_openai, query_service_with_reranker):
        # Setup
        mock_hyde_response = Mock()
        mock_hyde_response.choices = [Mock()]
        mock_hyde_response.choices[0].message.content = "hyde query"
        
        mock_final_response = Mock()
        mock_final_response.choices = [Mock()]
        mock_final_response.choices[0].message.content = '{"answer": "test"}'
        
        mock_openai.side_effect = [mock_hyde_response, mock_final_response]
        
        with patch.object(query_service_with_reranker, 'rerank', return_value=["context"]):
            query_service_with_reranker.chroma_db.query.return_value = {"metadatas": [[]]}
            
            # Execute
            query_service_with_reranker.query("test query", "Canada")
        
        # Verify final response system prompt
        final_call_args = mock_openai.call_args_list[1]
        system_message = final_call_args[1]['messages'][0]['content']
        
        assert "Answer the users QUESTION using the DOCUMENT text above" in system_message
        assert "Keep your answer ground in the facts of the DOCUMENT" in system_message
        assert "Only use relevant information from the DOCUMENT" in system_message
    
    def test_hyde_system_prompt_content(self, query_service_with_reranker):
        # Test that HyDE system prompt is properly structured
        with patch('service.query.openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "hypothetical doc"
            mock_openai.return_value = mock_response
            
            query_service_with_reranker.hyde("test query")
            
            call_args = mock_openai.call_args
            system_message = call_args[1]['messages'][0]['content']
            
            assert "Hypothetical Document Embedding" in system_message
            assert "DON'T ANSWER" in system_message