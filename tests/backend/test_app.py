import pytest
import sys
import os
import re
import json
import requests
from unittest.mock import patch, MagicMock
import numpy as np
from flask import Flask, request

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import app as app_module
from app import app, get_prices, plot_prices, get_exchange_rate, format_number


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestApp:
    @pytest.fixture(autouse=True)
    def mock_exchange_rate(self):
        """Mock the exchange rate API response."""
        with patch('app.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"venta": "400.0 ARS"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            yield mock_get

    def test_index_get(self, client):
        """Test the index page GET route."""
        response = client.get('/')
        assert response.status_code == 200
        # Check for a more general string that is present in the index page
        assert b'<!DOCTYPE html>' in response.data
        assert b'<html' in response.data

    def test_index_post_valid(self, client):
        """Test the index page POST route with valid data."""
        response = client.post('/', data={"item": "iphone", "number_of_pages": "1"})
        assert response.status_code == 302  # Redirect status
        assert "/show_plot?item=iphone&number_of_pages=1" in response.location

    def test_index_post_invalid_item(self, client):
        """Test the index page POST route with invalid item."""
        response = client.post('/', data={"item": "invalid@item", "number_of_pages": "1"})
        assert response.status_code == 400
        assert b'Invalid item parameter' in response.data

    def test_index_post_invalid_pages(self, client):
        """Test the index page POST route with invalid number of pages."""
        response = client.post('/', data={"item": "iphone", "number_of_pages": "5"})
        assert response.status_code == 400
        assert b'Number of pages must be between 1 and 3' in response.data

    def test_index_post_invalid_page_type(self, client):
        """Test the index page POST route with non-integer number of pages."""
        response = client.post('/', data={"item": "iphone", "number_of_pages": "abc"})
        assert response.status_code == 400
        assert b'Number of pages must be a valid integer' in response.data

    def test_manifest_route(self, client):
        """Test the manifest.json route."""
        response = client.get('/manifest.json')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_sw_route(self, client):
        """Test the sw.js route."""
        response = client.get('/sw.js')
        assert response.status_code == 200
        assert 'application/javascript' in response.content_type

    def test_assetlinks_route(self, client):
        """Test the assetlinks.json route."""
        response = client.get('/.well-known/assetlinks.json')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    @patch('app.get_prices')
    @patch('app.plot_prices')
    @patch('app.get_exchange_rate')
    def test_show_plot_success(self, mock_exchange, mock_plot, mock_get_prices, client):
        """Test the show_plot route with successful data retrieval."""
        # Mock data
        prices = [100000, 150000, 200000]
        mock_get_prices.return_value = (prices, "https://example.com", 0)
        mock_plot.return_value = "base64_encoded_image"
        mock_exchange.return_value = "400.0 ARS"
        
        response = client.get('/show_plot?item=iphone&number_of_pages=1')
        
        assert response.status_code == 200
        assert b'base64_encoded_image' in response.data
        mock_get_prices.assert_called_once_with("iphone", 1)
        mock_plot.assert_called_once()

    @patch('app.get_prices')
    def test_show_plot_no_prices(self, mock_get_prices, client):
        """Test the show_plot route when no prices are found."""
        mock_get_prices.return_value = (None, None, 0)
        
        response = client.get('/show_plot?item=nonexistentitem&number_of_pages=1')
        
        assert response.status_code == 500
        assert b'Failed to fetch prices' in response.data

    def test_show_plot_invalid_parameters(self, client):
        """Test the show_plot route with invalid parameters."""
        response = client.get('/show_plot?item=invalid@item&number_of_pages=1')
        assert response.status_code == 400
        assert b'Invalid item parameter' in response.data

    def test_format_number(self):
        """Test the format_number template filter."""
        assert format_number(1000) == "1,000"
        assert format_number("not a number") == "not a number"

    @patch('app.requests.get')
    def test_get_exchange_rate(self, mock_get):
        """Test the get_exchange_rate function."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"venta": "400.0 ARS"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        rate = get_exchange_rate()
        assert rate == "400.0 ARS"
        mock_get.assert_called_once_with("https://fastapiproject-1-eziw.onrender.com/blue")

    @patch('app.exchange_rate', None)
    @patch('app.requests.get')
    def test_get_exchange_rate_error(self, mock_get):
        """Test the get_exchange_rate function when an error occurs."""
        # Configure mock to raise an exception
        mock_get.side_effect = requests.exceptions.RequestException("API error")
        
        # Mock the logger to prevent error logs in test output
        with patch('app.app.logger.error'):
            rate = get_exchange_rate()
            assert rate is None

    @patch('app.requests.get')
    @patch('app.BeautifulSoup')
    def test_get_prices(self, mock_bs, mock_get):
        """Test the get_prices function."""
        # Mock the BeautifulSoup response
        mock_soup = MagicMock()
        mock_price_span1 = MagicMock()
        mock_price_span1.text = "100,000"
        mock_price_span2 = MagicMock()
        mock_price_span2.text = "150,000"
        mock_soup.find_all.return_value = [mock_price_span1, mock_price_span2]
        mock_bs.return_value = mock_soup
        
        # Mock the requests response
        mock_response = MagicMock()
        mock_get.return_value = mock_response
        
        prices, url, failed_pages = get_prices("iphone", 1)
        
        assert prices == [100000, 150000]
        assert url == "https://listado.mercadolibre.com.ar/iphone_Desde_1_NoIndex_True"
        assert failed_pages == 0

    def test_plot_prices(self):
        """Test the plot_prices function."""
        # Create test data
        prices = [100000, 150000, 200000]
        item = "iphone"
        url = "https://example.com"
        failed_pages = 0
        
        # Set up mocks
        with patch('app.get_exchange_rate') as mock_exchange, \
             patch('app.plt') as mock_plt, \
             patch('app.io.BytesIO') as mock_bytesio, \
             patch('app.base64.b64encode') as mock_b64, \
             app.test_request_context('/?number_of_pages=1'):  # Create a request context
            
            # Configure mocks
            mock_exchange.return_value = "400.0 ARS"
            
            mock_buffer = MagicMock()
            mock_buffer.getvalue.return_value = b"image_data"
            mock_bytesio.return_value = mock_buffer
            
            mock_b64.return_value = b"base64_encoded_image"
            
            # Call the function
            result = plot_prices(prices, item, url, failed_pages)
            
            # Verify results
            assert result == "base64_encoded_image"
            mock_plt.figure.assert_called_once()
            mock_plt.hist.assert_called_once()
            mock_plt.savefig.assert_called_once()
