import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from service.embedder import BGEM3EmbeddingFunction


class TestBGEM3EmbeddingFunction:
    
    @pytest.fixture
    def embedder(self):
        with patch('service.embedder.BGEM3FlagModel') as mock_model:
            mock_instance = Mock()
            mock_model.return_value = mock_instance
            embedder = BGEM3EmbeddingFunction()
            embedder.model = mock_instance
            return embedder
    
    def test_init_creates_model_instance(self):
        with patch('service.embedder.BGEM3FlagModel') as mock_model:
            mock_instance = Mock()
            mock_model.return_value = mock_instance
            
            embedder = BGEM3EmbeddingFunction()
            
            mock_model.assert_called_once_with('BAAI/bge-m3', use_fp16=True)
            assert embedder.model == mock_instance
    
    def test_call_with_single_document(self, embedder):
        # Setup
        mock_dense_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        embedder.model.encode.return_value = {"dense_vecs": mock_dense_vectors}
        
        input_docs = ["This is a test document"]
        
        # Execute
        result = embedder(input_docs)
        
        # Verify
        embedder.model.encode.assert_called_once_with(
            input_docs, 
            return_dense=True, 
            return_sparse=False
        )
        
        expected_result = np.array(mock_dense_vectors)
        np.testing.assert_array_equal(result, expected_result)
        assert isinstance(result, np.ndarray)
    
    def test_call_with_multiple_documents(self, embedder):
        # Setup
        mock_dense_vectors = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ]
        embedder.model.encode.return_value = {"dense_vecs": mock_dense_vectors}
        
        input_docs = [
            "First test document",
            "Second test document", 
            "Third test document"
        ]
        
        # Execute
        result = embedder(input_docs)
        
        # Verify
        embedder.model.encode.assert_called_once_with(
            input_docs,
            return_dense=True,
            return_sparse=False
        )
        
        expected_result = np.array(mock_dense_vectors)
        np.testing.assert_array_equal(result, expected_result)
        assert result.shape == (3, 3)
    
    def test_call_with_empty_documents(self, embedder):
        # Setup
        mock_dense_vectors = []
        embedder.model.encode.return_value = {"dense_vecs": mock_dense_vectors}
        
        input_docs = []
        
        # Execute
        result = embedder(input_docs)
        
        # Verify
        embedder.model.encode.assert_called_once_with(
            input_docs,
            return_dense=True,
            return_sparse=False
        )
        
        expected_result = np.array(mock_dense_vectors)
        np.testing.assert_array_equal(result, expected_result)
        assert result.shape == (0,)
    
    def test_call_with_long_documents(self, embedder):
        # Setup
        long_text = "This is a very long document. " * 100
        mock_dense_vectors = [[0.1] * 768]  # Typical embedding dimension
        embedder.model.encode.return_value = {"dense_vecs": mock_dense_vectors}
        
        input_docs = [long_text]
        
        # Execute
        result = embedder(input_docs)
        
        # Verify
        embedder.model.encode.assert_called_once_with(
            input_docs,
            return_dense=True,
            return_sparse=False
        )
        
        expected_result = np.array(mock_dense_vectors)
        np.testing.assert_array_equal(result, expected_result)
        assert result.shape == (1, 768)
    
    def test_model_encode_error_handling(self, embedder):
        # Setup
        embedder.model.encode.side_effect = Exception("Model encoding failed")
        
        input_docs = ["Test document"]
        
        # Execute & Verify
        with pytest.raises(Exception, match="Model encoding failed"):
            embedder(input_docs)
    
    def test_missing_dense_vecs_in_response(self, embedder):
        # Setup
        embedder.model.encode.return_value = {"sparse_vecs": []}  # Missing dense_vecs
        
        input_docs = ["Test document"]
        
        # Execute & Verify
        with pytest.raises(KeyError):
            embedder(input_docs)
    
    def test_numpy_array_conversion_with_nested_lists(self, embedder):
        # Setup
        mock_dense_vectors = [[[0.1, 0.2]], [[0.3, 0.4]]]  # Nested structure
        embedder.model.encode.return_value = {"dense_vecs": mock_dense_vectors}
        
        input_docs = ["Doc 1", "Doc 2"]
        
        # Execute
        result = embedder(input_docs)
        
        # Verify
        expected_result = np.array(mock_dense_vectors)
        np.testing.assert_array_equal(result, expected_result)
        assert isinstance(result, np.ndarray)
    
    def test_call_preserves_document_order(self, embedder):
        # Setup
        mock_dense_vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        embedder.model.encode.return_value = {"dense_vecs": mock_dense_vectors}
        
        input_docs = ["First", "Second", "Third"]
        
        # Execute
        result = embedder(input_docs)
        
        # Verify that order is preserved
        expected_result = np.array(mock_dense_vectors)
        np.testing.assert_array_equal(result, expected_result)
        
        # First document should map to first embedding
        np.testing.assert_array_equal(result[0], [1.0, 0.0, 0.0])
        np.testing.assert_array_equal(result[1], [0.0, 1.0, 0.0])
        np.testing.assert_array_equal(result[2], [0.0, 0.0, 1.0])