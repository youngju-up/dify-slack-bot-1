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
            inputs: Optional[Dict[str, Any]] = None,
            update_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Send a message to Dify API.

        Args:
            user_id: Unique user identifier
            message: The message text
            conversation_id: Optional conversation ID for context
            files: Optional list of files to include
            inputs: Optional input parameters
            update_callback: Optional callback function for real-time updates (text, is_final)

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
            
            # Log file information for debugging
            if files:
                logger.info(f"Files being sent: {[{'type': f['type'], 'url': f['url'][:50] + '...' if len(f['url']) > 50 else f['url']} for f in files]}")

            if Config.RESPONSE_MODE == "streaming":
                return self._handle_streaming_response(url, data, update_callback)
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
            error_detail = response.text
            logger.error(f"API error: {response.status_code} - {error_detail}")
            
            # Provide more specific error messages
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        raise Exception(f"API error: {error_data['message']}")
                except:
                    pass
            raise Exception(f"API error: {response.status_code}")

        return response.json()

    def _handle_streaming_response(self, url: str, data: Dict[str, Any], update_callback=None) -> Dict[str, Any]:
        """Handle streaming mode response with optional real-time updates."""
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
                parsed_data = parse_streaming_response(line_str)

                if parsed_data:
                    event = parsed_data.get('event')

                    if event == 'message':
                        chunk = parsed_data.get('answer', '')
                        full_answer += chunk
                        
                        # Call update callback if provided for real-time updates
                        if update_callback:
                            update_callback(full_answer, is_final=False)
                        
                        if not conversation_id:
                            conversation_id = parsed_data.get('conversation_id')
                        if not message_id:
                            message_id = parsed_data.get('message_id')

                    elif event == 'message_end':
                        metadata = parsed_data.get('metadata', {})
                        # Final update
                        if update_callback:
                            update_callback(full_answer, is_final=True)
                        break

        return {
            'answer': full_answer,
            'conversation_id': conversation_id,
            'message_id': message_id,
            'metadata': metadata
        }

    def upload_file(self, file_content: bytes, filename: str, user_id: str) -> Dict[str, Any]:
        """
        Upload a file to Dify and return the file URL.

        Args:
            file_content: File content as bytes
            filename: Name of the file
            user_id: User identifier

        Returns:
            File upload response with file URL
        """
        # Try different possible endpoints for file upload
        possible_endpoints = [
            f"{self.base_url}/files/upload",
            f"{self.base_url}/upload",
            f"{self.base_url}/v1/files/upload",
            f"{self.base_url}/v1/upload"
        ]
        
        # Prepare file data - use form data format as per Dify API spec
        files = {
            'file': (filename, file_content, self._get_content_type(filename)),
            'user': (None, user_id)  # Include user as form field
        }

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Try each endpoint until one works
        last_error = None
        for url in possible_endpoints:
            try:
                logger.info(f"Trying file upload endpoint: {url}")
                logger.debug(f"File details: {filename}, size: {len(file_content)} bytes, user: {user_id}")
                
                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    timeout=self.timeout
                )
                
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response body: {response.text[:500]}...")
                
                # Log success for 201 status
                if response.status_code == 201:
                    logger.info(f"File created successfully (201) - {filename}")
                
                if response.status_code in [200, 201]:  # 201 = Created
                    logger.info(f"File upload successful using endpoint: {url}")
                    result = response.json()
                    
                    # Extract file ID from response (for local_file method)
                    file_id = result.get('id')
                    if file_id:
                        logger.info(f"File uploaded successfully with ID: {file_id}")
                        return {
                            'id': file_id,
                            'type': self._get_file_type_from_filename(filename),
                            'original_response': result
                        }
                    else:
                        logger.warning(f"No file ID found in response: {result}")
                        return result
                        
                elif response.status_code != 404:  # Don't try next endpoint for 404
                    last_error = response
                    logger.warning(f"File upload failed on {url}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.warning(f"Exception trying endpoint {url}: {e}")
                last_error = e
                continue
        
        # If all endpoints failed, use the last error
        if last_error and hasattr(last_error, 'status_code'):
            response = last_error
        else:
            raise Exception("All file upload endpoints failed")

        # Handle the final error
        if response.status_code not in [200, 201]:
            error_detail = response.text
            logger.error(f"File upload error: {response.status_code} - {error_detail}")
            
            # Provide more specific error messages
            if response.status_code == 415:
                raise Exception(f"File type not supported by Dify API. Please try a different file format.")
            elif response.status_code == 413:
                raise Exception(f"File too large. Maximum size allowed is {Config.MAX_FILE_SIZE // (1024*1024)}MB.")
            elif response.status_code == 400:
                raise Exception(f"Invalid file format or corrupted file.")
            else:
                raise Exception(f"File upload failed: {response.status_code} - {error_detail}")

        return response.json()

    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension."""
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        
        # Ensure we have a proper content type
        if not content_type:
            # Fallback based on file extension
            ext = filename.lower().split('.')[-1]
            type_mapping = {
                'png': 'image/png',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'gif': 'image/gif',
                'webp': 'image/webp',
                'pdf': 'application/pdf',
                'txt': 'text/plain',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'xls': 'application/vnd.ms-excel',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            content_type = type_mapping.get(ext, 'application/octet-stream')
        
        return content_type

    def _get_file_type_from_filename(self, filename: str) -> str:
        """Get Dify file type based on file extension according to API spec."""
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        
        logger.debug(f"Determining file type for {filename}: content_type={content_type}")
        
        # Map to Dify API supported types (lowercase)
        if content_type:
            if content_type.startswith('image/'):
                logger.debug(f"File type determined as: image")
                return 'image'
            elif content_type in ['text/plain', 'text/markdown', 'application/pdf',
                                'text/html', 'application/vnd.ms-excel',
                                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                'application/msword',
                                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                'text/csv', 'application/xml', 'application/epub+zip',
                                'application/vnd.ms-powerpoint',
                                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                                'message/rfc822', 'application/vnd.ms-outlook']:
                logger.debug(f"File type determined as: document")
                return 'document'
            elif content_type.startswith('audio/'):
                logger.debug(f"File type determined as: audio")
                return 'audio'
            elif content_type.startswith('video/'):
                logger.debug(f"File type determined as: video")
                return 'video'
        
        # Fallback based on file extension
        ext = filename.lower().split('.')[-1]
        if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']:
            logger.debug(f"File type determined as: image (by extension)")
            return 'image'
        elif ext in ['mp3', 'm4a', 'wav', 'webm', 'amr']:
            logger.debug(f"File type determined as: audio (by extension)")
            return 'audio'
        elif ext in ['mp4', 'mov', 'mpeg', 'mpga']:
            logger.debug(f"File type determined as: video (by extension)")
            return 'video'
        elif ext in ['txt', 'md', 'markdown', 'pdf', 'html', 'xlsx', 'xls', 'docx', 'csv', 
                    'eml', 'msg', 'pptx', 'ppt', 'xml', 'epub']:
            logger.debug(f"File type determined as: document (by extension)")
            return 'document'
        else:
            logger.debug(f"File type determined as: custom (by extension)")
            return 'custom'

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

    def check_file_upload_support(self) -> bool:
        """Check if the Dify API supports file uploads."""
        try:
            # Try to get app info to check if file upload is supported
            app_info = self.get_app_info()
            
            # Check if the app has file upload capabilities
            # This is a basic check - the actual implementation depends on Dify's API structure
            logger.info("Checking file upload support...")
            
            # Try a simple HEAD request to the upload endpoint
            test_endpoints = [
                f"{self.base_url}/files/upload",
                f"{self.base_url}/upload",
                f"{self.base_url}/v1/files/upload"
            ]
            
            for endpoint in test_endpoints:
                try:
                    response = requests.head(endpoint, headers=self.headers, timeout=5)
                    if response.status_code in [200, 405]:  # 405 means method not allowed but endpoint exists
                        logger.info(f"File upload endpoint exists: {endpoint}")
                        return True
                except:
                    continue
                    
            logger.warning("No file upload endpoints found")
            return False
            
        except Exception as e:
            logger.error(f"Error checking file upload support: {e}")
            return False
