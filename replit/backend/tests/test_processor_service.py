import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
import io
from PIL import Image
import base64

from service.processor import PDFProcessor


class TestPDFProcessor:
    
    @pytest.fixture
    def processor(self):
        return PDFProcessor()
    
    def test_init(self, processor):
        assert isinstance(processor, PDFProcessor)
    
    @patch('service.processor.openai.chat.completions.create')
    def test_summarize_from_table_success(self, mock_openai, processor):
        # Setup
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This table shows budget allocation priorities for education and healthcare."
        mock_openai.return_value = mock_response
        
        markdown_table = "| Category | Budget |\n| Education | 500M |\n| Healthcare | 300M |"
        
        # Execute
        result = processor.summarize_from_table(markdown_table)
        
        # Verify
        assert result == "This table shows budget allocation priorities for education and healthcare."
        mock_openai.assert_called_once()
        
        # Verify the call structure
        call_args = mock_openai.call_args
        assert call_args[1]['model'] == 'gpt-4o'
        assert call_args[1]['max_tokens'] == 256
        assert len(call_args[1]['messages']) == 2
        assert call_args[1]['messages'][0]['role'] == 'system'
        assert call_args[1]['messages'][1]['role'] == 'user'
        assert call_args[1]['messages'][1]['content'] == markdown_table
    
    @patch('service.processor.openai.chat.completions.create')
    def test_summarize_from_table_openai_error(self, mock_openai, processor):
        # Setup
        mock_openai.side_effect = Exception("OpenAI API error")
        
        markdown_table = "| Category | Budget |"
        
        # Execute & Verify
        with pytest.raises(Exception, match="OpenAI API error"):
            processor.summarize_from_table(markdown_table)
    
    @patch('service.processor.openai.chat.completions.create')
    @patch('service.processor.Image.open')
    def test_summarize_from_image_bytes_success(self, mock_image_open, mock_openai, processor):
        # Setup
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "The image shows a political rally with campaign banners."
        mock_openai.return_value = mock_response
        
        # Mock PIL Image
        mock_pil_image = Mock()
        mock_pil_image.format = "PNG"
        mock_image_open.return_value = mock_pil_image
        
        # Mock save method
        mock_buffer = io.BytesIO()
        mock_pil_image.save = Mock()
        
        image_bytes = b"fake_image_data"
        image_ext = "png"
        context_text = "Political rally context"
        
        with patch('io.BytesIO') as mock_bytesio:
            mock_bytesio.return_value.getvalue.return_value = b"encoded_image"
            
            with patch('base64.b64encode') as mock_b64:
                mock_b64.return_value.decode.return_value = "base64encodedstring"
                
                # Execute
                result = processor.summarize_from_image_bytes(image_bytes, image_ext, context_text)
        
        # Verify
        assert result == "The image shows a political rally with campaign banners."
        mock_openai.assert_called_once()
        
        # Verify OpenAI call structure
        call_args = mock_openai.call_args
        assert call_args[1]['model'] == 'gpt-4o'
        assert call_args[1]['max_tokens'] == 256
        assert len(call_args[1]['messages']) == 2
        assert call_args[1]['messages'][1]['content'][0]['text'] == context_text
        assert 'image_url' in call_args[1]['messages'][1]['content'][1]
    
    def test_is_inside_table_true(self, processor):
        # Setup
        block = [10, 20, 50, 60, "text", 0, 0]  # bx0, by0, bx1, by1
        mock_table = Mock()
        mock_table.bbox = (5, 15, 55, 65)  # tx0, ty0, tx1, ty1
        tables = [mock_table]
        
        # Execute
        result = processor.is_inside_table(block, tables)
        
        # Verify
        assert result is True
    
    def test_is_inside_table_false(self, processor):
        # Setup
        block = [10, 20, 50, 60, "text", 0, 0]  # Outside table bounds
        mock_table = Mock()
        mock_table.bbox = (70, 80, 90, 100)  # Table is elsewhere
        tables = [mock_table]
        
        # Execute
        result = processor.is_inside_table(block, tables)
        
        # Verify
        assert result is False
    
    def test_is_inside_table_multiple_tables(self, processor):
        # Setup
        block = [10, 20, 50, 60, "text", 0, 0]
        
        mock_table1 = Mock()
        mock_table1.bbox = (70, 80, 90, 100)  # Block not inside this one
        
        mock_table2 = Mock()
        mock_table2.bbox = (5, 15, 55, 65)  # Block is inside this one
        
        tables = [mock_table1, mock_table2]
        
        # Execute
        result = processor.is_inside_table(block, tables)
        
        # Verify
        assert result is True
    
    def test_is_inside_table_empty_tables(self, processor):
        # Setup
        block = [10, 20, 50, 60, "text", 0, 0]
        tables = []
        
        # Execute
        result = processor.is_inside_table(block, tables)
        
        # Verify
        assert result is False
    
    @patch('service.processor.fitz.open')
    @patch('builtins.open', new_callable=mock_open)
    def test_pdf_to_txt_success(self, mock_file, mock_fitz, processor):
        # Setup
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.number = 0
        mock_page.get_images.return_value = []
        mock_page.find_tables.return_value.tables = []
        mock_page.get_text.return_value = [
            [0, 0, 100, 20, "Test document text", 0, 0]
        ]
        
        mock_pdf.__iter__ = Mock(return_value=iter([mock_page]))
        mock_fitz.return_value.__enter__.return_value = mock_pdf
        
        pdf_path = "/path/to/test.pdf"
        txt_path = "/path/to/output.txt"
        
        # Execute
        result = processor.pdf_to_txt(pdf_path, txt_path)
        
        # Verify
        assert result['success'] is True
        assert 'text_length' in result
        assert result['output_path'] == txt_path
        
        mock_fitz.assert_called_once_with(pdf_path)
        mock_file.assert_called_once_with(txt_path, 'w', encoding='utf-8')
    
    @patch('service.processor.fitz.open')
    @patch('builtins.open', new_callable=mock_open)
    def test_pdf_to_txt_with_images(self, mock_file, mock_fitz, processor):
        # Setup
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.number = 0
        
        # Mock image data
        mock_page.get_images.return_value = [(123, 0, 100, 100, 0, 'png', 'image', None)]
        mock_pdf.extract_image.return_value = {
            'image': b'fake_image_data',
            'ext': 'png'
        }
        
        # Mock image info and bbox
        mock_page.get_image_info.return_value = [{'bbox': (10, 10, 50, 50)}]
        mock_page.get_text.return_value = [
            [0, 0, 100, 5, "Context before image", 0, 0],
            [0, 60, 100, 80, "Text after image", 0, 0]
        ]
        
        mock_page.find_tables.return_value.tables = []
        
        mock_pdf.__iter__ = Mock(return_value=iter([mock_page]))
        mock_fitz.return_value.__enter__.return_value = mock_pdf
        
        with patch.object(processor, 'summarize_from_image_bytes') as mock_summarize:
            mock_summarize.return_value = "Image shows political chart"
            
            # Execute
            result = processor.pdf_to_txt("/path/to/test.pdf", "/path/to/output.txt")
        
        # Verify
        assert result['success'] is True
        mock_summarize.assert_called_once()
    
    @patch('service.processor.fitz.open')
    @patch('builtins.open', new_callable=mock_open)
    def test_pdf_to_txt_with_tables(self, mock_file, mock_fitz, processor):
        # Setup
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.number = 0
        mock_page.get_images.return_value = []
        
        # Mock table data
        mock_table = Mock()
        mock_table.to_markdown.return_value = "| Col1 | Col2 |\n| A | B |"
        mock_table.bbox = (10, 10, 50, 50)
        mock_page.find_tables.return_value.tables = [mock_table]
        
        mock_page.get_text.return_value = [
            [0, 0, 100, 5, "Text before table", 0, 0],
            [15, 15, 45, 45, "Table content", 0, 0],  # Inside table
            [0, 60, 100, 80, "Text after table", 0, 0]
        ]
        
        mock_pdf.__iter__ = Mock(return_value=iter([mock_page]))
        mock_fitz.return_value.__enter__.return_value = mock_pdf
        
        with patch.object(processor, 'summarize_from_table') as mock_summarize:
            mock_summarize.return_value = "Table shows data comparison"
            
            # Execute
            result = processor.pdf_to_txt("/path/to/test.pdf", "/path/to/output.txt")
        
        # Verify
        assert result['success'] is True
        mock_summarize.assert_called_once_with("| Col1 | Col2 |\n| A | B |")
    
    @patch('service.processor.fitz.open')
    def test_pdf_to_txt_dashboard_success(self, mock_fitz, processor):
        # Setup
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.number = 0
        mock_page.get_images.return_value = []
        mock_page.find_tables.return_value.tables = []
        mock_page.get_text.return_value = [
            [0, 0, 100, 20, "Dashboard test text", 0, 0]
        ]
        
        mock_pdf.__iter__ = Mock(return_value=iter([mock_page]))
        mock_fitz.return_value.__enter__.return_value = mock_pdf
        
        pdf_content = b"fake_pdf_content"
        
        # Execute
        result = processor.pdf_to_txt_dashboard(pdf_content)
        
        # Verify
        assert result['success'] is True
        assert 'text' in result
        assert "Dashboard test text" in result['text']
        
        mock_fitz.assert_called_once_with(stream=pdf_content, filetype="pdf")
    
    @patch('service.processor.fitz.open')
    def test_pdf_to_txt_file_error(self, mock_fitz, processor):
        # Setup
        mock_fitz.side_effect = Exception("Failed to open PDF")
        
        # Execute & Verify
        with pytest.raises(Exception, match="Failed to open PDF"):
            processor.pdf_to_txt("/invalid/path.pdf", "/output.txt")
    
    @patch('service.processor.fitz.open')
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_pdf_to_txt_write_error(self, mock_file, mock_fitz, processor):
        # Setup
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.number = 0
        mock_page.get_images.return_value = []
        mock_page.find_tables.return_value.tables = []
        mock_page.get_text.return_value = []
        
        mock_pdf.__iter__ = Mock(return_value=iter([mock_page]))
        mock_fitz.return_value.__enter__.return_value = mock_pdf
        
        # Execute & Verify
        with pytest.raises(PermissionError, match="Permission denied"):
            processor.pdf_to_txt("/path/to/test.pdf", "/protected/output.txt")
    
    @patch('service.processor.fitz.open')
    def test_pdf_to_txt_dashboard_empty_pdf(self, mock_fitz, processor):
        # Setup
        mock_pdf = Mock()
        mock_pdf.__iter__ = Mock(return_value=iter([]))  # No pages
        mock_fitz.return_value.__enter__.return_value = mock_pdf
        
        pdf_content = b"empty_pdf_content"
        
        # Execute
        result = processor.pdf_to_txt_dashboard(pdf_content)
        
        # Verify
        assert result['success'] is True
        assert result['text'] == ""
    
    @patch('service.processor.openai.chat.completions.create')
    def test_summarize_from_table_system_prompt_content(self, mock_openai, processor):
        # Setup
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Analysis result"
        mock_openai.return_value = mock_response
        
        # Execute
        processor.summarize_from_table("test table")
        
        # Verify system prompt contains political analysis instructions
        call_args = mock_openai.call_args
        system_message = call_args[1]['messages'][0]['content']
        assert "political platform document" in system_message
        assert "party's priorities" in system_message
        assert "policies" in system_message
    
    @patch('service.processor.openai.chat.completions.create')
    @patch('service.processor.Image.open')
    def test_summarize_from_image_bytes_system_prompt_content(self, mock_image_open, mock_openai, processor):
        # Setup
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Image analysis result"
        mock_openai.return_value = mock_response
        
        mock_pil_image = Mock()
        mock_pil_image.format = "PNG"
        mock_image_open.return_value = mock_pil_image
        
        with patch('io.BytesIO'), patch('base64.b64encode') as mock_b64:
            mock_b64.return_value.decode.return_value = "base64string"
            
            # Execute
            processor.summarize_from_image_bytes(b"image", "png", "context")
        
        # Verify system prompt contains political document analysis instructions
        call_args = mock_openai.call_args
        system_message = call_args[1]['messages'][0]['content']
        assert "political party platform documents" in system_message
        assert "PyMuPDF" in system_message
        assert "cannot be interpreted" in system_message