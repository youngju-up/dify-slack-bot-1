"""
Dify API client for handling all interactions with the Dify service.
"""
import requests
import json
from typing import Dict, Any, Optional, List, Generator
from .config import Config
from .utils import logger, parse_streaming_response


class DifyClient:
    """Client for interacting with Dify API."""

    def __init__(self):
        self.base_url = Config.DIFY_BASE_URL
        self.api_key = Config.DIFY_API_KEY
        self.timeout = Config.REQUEST_TIMEOUT
        self.headers = Config.get_headers()

    def send_message(
            self,
            user_id: str,
            message: str,
            conversation_id: Optional[str] = None,
            files: Optional[List[Dict[str, Any]]] = None,
            inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to Dify API.

        Args:
            user_id: Unique user identifier
            message: The message text
            conversation_id: Optional conversation ID for context
            files: Optional list of files to include
            inputs: Optional input parameters

        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/chat-messages"

        data = {
            "query": message,
            "inputs": inputs or {},
            "response_mode": Config.RESPONSE_MODE,
            "user": user_id,
            "auto_generate_name": True
        }

        if conversation_id:
            data["conversation_id"] = conversation_id

        if files:
            data["files"] = files

        try:
            logger.debug(f"Sending message to Dify: {data}")

            if Config.RESPONSE_MODE == "streaming":
                return self._handle_streaming_response(url, data)
            else:
                return self._handle_blocking_response(url, data)

        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            raise Exception("Request timeout")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            raise Exception("Connection error")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    def _handle_blocking_response(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle blocking mode response."""
        response = requests.post(
            url,
            headers=self.headers,
            json=data,
            timeout=self.timeout
        )

        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")

        return response.json()

    def _handle_streaming_response(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle streaming mode response."""
        response = requests.post(
            url,
            headers=self.headers,
            json=data,
            stream=True,
            timeout=self.timeout
        )

        if response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")

        # Collect streaming response
        full_answer = ""
        conversation_id = None
        message_id = None
        metadata = {}

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                data = parse_streaming_response(line_str)

                if data:
                    event = data.get('event')

                    if event == 'message':
                        full_answer += data.get('answer', '')
                        if not conversation_id:
                            conversation_id = data.get('conversation_id')
                        if not message_id:
                            message_id = data.get('message_id')

                    elif event == 'message_end':
                        metadata = data.get('metadata', {})
                        break

        return {
            'answer': full_answer,
            'conversation_id': conversation_id,
            'message_id': message_id,
            'metadata': metadata
        }

    def upload_file(self, file_content: bytes, filename: str, user_id: str) -> Dict[str, Any]:
        """
        Upload a file to Dify.

        Args:
            file_content: File content as bytes
            filename: Name of the file
            user_id: User identifier

        Returns:
            File upload response with file ID
        """
        url = f"{self.base_url}/files/upload"

        files = {'file': (filename, file_content)}
        data = {'user': user_id}

        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"File upload error: {response.status_code} - {response.text}")
                raise Exception(f"File upload error: {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise

    def get_conversations(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get conversation list for a user."""
        url = f"{self.base_url}/conversations"
        params = {
            "user": user_id,
            "limit": limit
        }

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            raise

    def get_messages(
            self,
            conversation_id: str,
            user_id: str,
            limit: int = 20
    ) -> Dict[str, Any]:
        """Get messages from a conversation."""
        url = f"{self.base_url}/messages"
        params = {
            "conversation_id": conversation_id,
            "user": user_id,
            "limit": limit
        }

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise

    def stop_generation(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """Stop a streaming generation."""
        url = f"{self.base_url}/chat-messages/{task_id}/stop"
        data = {"user": user_id}

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Error stopping generation: {e}")
            raise

    def send_feedback(
            self,
            message_id: str,
            rating: str,
            user_id: str,
            content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send feedback for a message."""
        url = f"{self.base_url}/messages/{message_id}/feedbacks"
        data = {
            "rating": rating,
            "user": user_id
        }

        if content:
            data["content"] = content

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Error sending feedback: {e}")
            raise

    def get_suggested_questions(self, message_id: str, user_id: str) -> List[str]:
        """Get suggested follow-up questions."""
        url = f"{self.base_url}/messages/{message_id}/suggested"
        params = {"user": user_id}

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")

            result = response.json()
            return result.get('data', [])

        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []

    def get_app_info(self) -> Dict[str, Any]:
        """Get application information."""
        url = f"{self.base_url}/info"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Error getting app info: {e}")
            raise

    def get_parameters(self) -> Dict[str, Any]:
        """Get application parameters."""
        url = f"{self.base_url}/parameters"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API error: {response.status_code}")

            return response.json()

        except Exception as e:
            logger.error(f"Error getting parameters: {e}")
            raise
