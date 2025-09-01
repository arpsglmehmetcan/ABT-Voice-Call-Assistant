import pytest
import tempfile
import os
import json
import numpy as np
import soundfile as sf
from io import BytesIO

# Import the Flask app
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, allowed_file, transcribe_audio, generate_llm_response


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_audio_file():
    """Create a sample audio file for testing"""
    # Generate a simple sine wave
    sample_rate = 16000
    duration = 2  # 2 seconds
    frequency = 440  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        sf.write(temp_file.name, audio_data, sample_rate)
        return temp_file.name


class TestVoiceAssistantAPI:
    """Test cases for Voice Assistant API"""

    def test_index_endpoint(self, client):
        """Test the index endpoint"""
        response = client.get('/')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'service' in data
        assert 'Voice Call Assistant API' in data['service']

    def test_health_endpoint(self, client):
        """Test the health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'healthy'
        assert 'whisper_loaded' in data
        assert 'timestamp' in data

    def test_ask_assistant_no_file(self, client):
        """Test ask_assistant endpoint without file"""
        response = client.post('/ask_assistant')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data
        assert 'No audio file provided' in data['error']

    def test_ask_assistant_empty_file(self, client):
        """Test ask_assistant endpoint with empty filename"""
        data = {'audio_file': (BytesIO(b''), '')}
        response = client.post('/ask_assistant', data=data)
        assert response.status_code == 400

        result = json.loads(response.data)
        assert 'error' in result

    def test_ask_assistant_invalid_file_type(self, client):
        """Test ask_assistant endpoint with invalid file type"""
        data = {'audio_file': (BytesIO(b'fake content'), 'test.txt')}
        response = client.post('/ask_assistant', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

        result = json.loads(response.data)
        assert 'File type not allowed' in result['error']

    def test_ask_assistant_with_audio(self, client, sample_audio_file):
        """Test ask_assistant endpoint with valid audio file"""
        try:
            with open(sample_audio_file, 'rb') as audio_file:
                data = {
                    'audio_file': (audio_file, 'test_audio.wav')
                }
                response = client.post('/ask_assistant', data=data)

                # Should return 200 even with synthetic audio
                assert response.status_code == 200

                result = json.loads(response.data)
                assert 'transcribed_text' in result
                assert 'assistant_response' in result

                # Response should be non-empty strings
                assert isinstance(result['transcribed_text'], str)
                assert isinstance(result['assistant_response'], str)

        finally:
            # Clean up
            if os.path.exists(sample_audio_file):
                os.unlink(sample_audio_file)


class TestUtilityFunctions:
    """Test utility functions"""

    def test_allowed_file_valid_extensions(self):
        """Test allowed_file function with valid extensions"""
        valid_files = [
            'test.wav',
            'audio.mp3',
            'recording.mp4',
            'voice.m4a',
            'music.flac',
            'sound.ogg'
        ]

        for filename in valid_files:
            assert allowed_file(filename) == True

    def test_allowed_file_invalid_extensions(self):