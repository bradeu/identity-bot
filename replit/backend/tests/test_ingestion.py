import pytest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

from service.ingestion import IngestionService


class TestIngestionService:
    
    @pytest.fixture
    def mock_chroma_db(self):
        return Mock()
    
    @pytest.fixture
    def ingestion_service(self, mock_chroma_db):
        return IngestionService(chroma_db=mock_chroma_db)
    
    def test_init_with_chroma_db(self, mock_chroma_db):
        service = IngestionService(chroma_db=mock_chroma_db)
        assert service.chroma_db == mock_chroma_db
    
    def test_init_without_chroma_db(self):
        service = IngestionService()
        assert service.chroma_db is None
    
    def test_load_text_success(self, ingestion_service):
        # Setup
        test_content = "This is test content\nwith multiple lines\nof text."
        mock_file = mock_open(read_data=test_content)
        
        with patch('builtins.open', mock_file):
            # Execute
            result = ingestion_service.load_text("/path/to/test.txt")
            
            # Verify
            assert result == test_content
            mock_file.assert_called_once_with("/path/to/test.txt", "r", encoding="utf-8")
    
    def test_load_text_file_not_found(self, ingestion_service):
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                ingestion_service.load_text("/nonexistent/file.txt")
    
    def test_load_text_permission_error(self, ingestion_service):
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                ingestion_service.load_text("/protected/file.txt")
    
    def test_split_text_basic(self, ingestion_service):
        text = "This is a test string for splitting"
        chunk_size = 10
        
        result = ingestion_service.split_text(text, chunk_size)
        
        expected = ["This is a ", "test strin", "g for spli", "tting"]
        assert result == expected
    
    def test_split_text_exact_division(self, ingestion_service):
        text = "abcdefghij"  # 10 characters
        chunk_size = 5
        
        result = ingestion_service.split_text(text, chunk_size)
        
        expected = ["abcde", "fghij"]
        assert result == expected
    
    def test_split_text_shorter_than_chunk(self, ingestion_service):
        text = "short"
        chunk_size = 10
        
        result = ingestion_service.split_text(text, chunk_size)
        
        expected = ["short"]
        assert result == expected
    
    def test_split_text_empty_string(self, ingestion_service):
        text = ""
        chunk_size = 10
        
        result = ingestion_service.split_text(text, chunk_size)
        
        expected = []
        assert result == expected
    
    def test_sliding_window_split_basic(self, ingestion_service):
        text = "abcdefghijklmnopqrs"  # 18 characters
        window_size = 6
        overlap = 2
        
        result = ingestion_service.sliding_window_split(text, window_size, overlap)
        
        # stride = 6-2 = 4, so windows at: 0, 4, 8, 12
        # Plus final window from end: [-6:]
        expected = ["abcdef", "efghij", "ijklmn", "mnopqr", "nopqrs"]
        assert result == expected
    
    def test_sliding_window_split_no_overlap(self, ingestion_service):
        text = "abcdefghijklmn"  # 14 characters
        window_size = 4
        overlap = 0
        
        result = ingestion_service.sliding_window_split(text, window_size, overlap)
        
        expected = ["abcd", "efgh", "ijkl", "klmn"]
        assert result == expected
    
    def test_sliding_window_split_overlap_equals_window_size(self, ingestion_service):
        text = "abcdefgh"
        window_size = 4
        overlap = 4  # Equal to window size
        
        with pytest.raises(ValueError, match="Overlap must be smaller than window size"):
            ingestion_service.sliding_window_split(text, window_size, overlap)
    
    def test_sliding_window_split_overlap_greater_than_window_size(self, ingestion_service):
        text = "abcdefgh"
        window_size = 4
        overlap = 5  # Greater than window size
        
        with pytest.raises(ValueError, match="Overlap must be smaller than window size"):
            ingestion_service.sliding_window_split(text, window_size, overlap)
    
    def test_sliding_window_split_text_shorter_than_window(self, ingestion_service):
        text = "abc"  # 3 characters
        window_size = 5
        overlap = 1
        
        result = ingestion_service.sliding_window_split(text, window_size, overlap)
        
        # When text is shorter than window, the implementation adds the final chunk
        expected = ["abc"]  # text[-window_size:] = text[-5:] = "abc"
        assert result == expected
    
    def test_sliding_window_split_empty_string(self, ingestion_service):
        text = ""
        window_size = 5
        overlap = 1
        
        result = ingestion_service.sliding_window_split(text, window_size, overlap)
        
        expected = []
        assert result == expected
    
    def test_sliding_window_split_includes_remainder(self, ingestion_service):
        text = "abcdefghijk"  # 11 characters
        window_size = 4
        overlap = 1
        
        result = ingestion_service.sliding_window_split(text, window_size, overlap)
        
        # Expected: stride = 4-1 = 3
        # Windows: [0:4], [3:7], [6:10], plus remainder [7:11]
        expected = ["abcd", "defg", "ghij", "hijk"]
        assert result == expected
    
    @patch('service.ingestion.get_collection_from_country')
    def test_ingest_text_by_country_success(self, mock_get_collection, ingestion_service):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        ingestion_service.chroma_db = Mock()
        
        full_text = "This is a test document\nwith multiple lines\nfor ingestion testing."
        country = "Canada"
        chunk_size = 20
        chunk_overlap = 5
        sliding_window = 10
        
        # Execute
        result = ingestion_service.ingest_text_by_country(
            full_text=full_text,
            country=country,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            sliding_window=sliding_window
        )
        
        # Verify
        assert result['success'] is True
        assert 'parent_chunks' in result
        assert 'total_child_chunks' in result
        
        # Verify MongoDB calls
        assert mock_collection.insert_one.call_count > 0
        
        # Verify ChromaDB calls
        assert ingestion_service.chroma_db.add_document_by_country.call_count > 0
    
    @patch('service.ingestion.get_collection_from_country')
    def test_ingest_text_by_country_removes_newlines(self, mock_get_collection, ingestion_service):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        ingestion_service.chroma_db = Mock()
        
        full_text = "Line one\nLine two\nLine three"
        country = "Germany"
        
        # Execute
        ingestion_service.ingest_text_by_country(full_text, country)
        
        # Verify that text with newlines removed was processed
        # Check the first call to insert_one
        call_args = mock_collection.insert_one.call_args_list[0][0][0]
        parent_chunk = call_args['parent_chunk']
        assert '\n' not in parent_chunk
        assert 'Line one Line two Line three' in parent_chunk
    
    @patch('service.ingestion.get_collection_from_country')
    def test_ingest_text_by_country_proper_metadata(self, mock_get_collection, ingestion_service):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        ingestion_service.chroma_db = Mock()
        
        full_text = "Short test text for metadata verification."
        country = "France"
        
        # Execute
        ingestion_service.ingest_text_by_country(full_text, country)
        
        # Verify MongoDB insert calls have correct structure
        mongo_calls = mock_collection.insert_one.call_args_list
        for call in mongo_calls:
            doc = call[0][0]
            assert 'parent_id' in doc
            assert 'parent_chunk' in doc
            assert doc['parent_id'].startswith('parent_')
        
        # Verify ChromaDB calls have correct structure
        chroma_calls = ingestion_service.chroma_db.add_document_by_country.call_args_list
        for call in chroma_calls:
            kwargs = call[1]
            assert kwargs['country'] == country
            assert 'documents' in kwargs
            assert 'ids' in kwargs
            assert 'metadatas' in kwargs
            
            # Check that child IDs reference parent IDs
            for child_id in kwargs['ids']:
                assert '_child_' in child_id
                assert child_id.startswith('parent_')
            
            # Check metadata structure
            for metadata in kwargs['metadatas']:
                assert 'parent_id' in metadata
                assert metadata['parent_id'].startswith('parent_')
    
    @patch('service.ingestion.get_collection_from_country')
    def test_ingest_text_by_country_default_parameters(self, mock_get_collection, ingestion_service):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        ingestion_service.chroma_db = Mock()
        
        full_text = "Test text for default parameters."
        country = "UK"
        
        # Execute with default parameters
        result = ingestion_service.ingest_text_by_country(full_text, country)
        
        # Verify it completes successfully with defaults
        assert result['success'] is True
        assert mock_collection.insert_one.called
        assert ingestion_service.chroma_db.add_document_by_country.called
    
    @patch('service.ingestion.get_collection_from_country')
    def test_ingest_text_by_country_mongo_error(self, mock_get_collection, ingestion_service):
        # Setup
        mock_collection = Mock()
        mock_collection.insert_one.side_effect = Exception("MongoDB connection failed")
        mock_get_collection.return_value = mock_collection
        ingestion_service.chroma_db = Mock()
        
        full_text = "Test text"
        country = "Japan"
        
        # Execute & Verify
        with pytest.raises(Exception, match="MongoDB connection failed"):
            ingestion_service.ingest_text_by_country(full_text, country)
    
    @patch('service.ingestion.get_collection_from_country')
    def test_ingest_text_by_country_chroma_error(self, mock_get_collection, ingestion_service):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        
        ingestion_service.chroma_db = Mock()
        ingestion_service.chroma_db.add_document_by_country.side_effect = Exception("ChromaDB error")
        
        full_text = "Test text"
        country = "Australia"
        
        # Execute & Verify
        with pytest.raises(Exception, match="ChromaDB error"):
            ingestion_service.ingest_text_by_country(full_text, country)
    
    @patch('service.ingestion.get_collection_from_country')
    def test_ingest_text_by_country_empty_text(self, mock_get_collection, ingestion_service):
        # Setup
        mock_collection = Mock()
        mock_get_collection.return_value = mock_collection
        ingestion_service.chroma_db = Mock()
        
        full_text = ""
        country = "India"
        
        # Execute
        result = ingestion_service.ingest_text_by_country(full_text, country)
        
        # Verify
        assert result['success'] is True
        assert result['parent_chunks'] == 0
        assert result['total_child_chunks'] == 0
        
        # Should not make any database calls for empty text
        mock_collection.insert_one.assert_not_called()
        ingestion_service.chroma_db.add_document_by_country.assert_not_called()