#!/usr/bin/env python3
"""
Debug script to check Dify API configuration and file upload support.
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_dify_api():
    """Check Dify API configuration and file upload support."""
    
    # Get configuration
    dify_base_url = os.environ.get("DIFY_BASE_URL", "http://agents.algolyzerlab.com/v1")
    dify_api_key = os.environ.get("DIFY_API_KEY")
    
    print(f"🔍 Checking Dify API Configuration")
    print(f"Base URL: {dify_base_url}")
    print(f"API Key: {'*' * len(dify_api_key) if dify_api_key else 'NOT SET'}")
    print("-" * 50)
    
    if not dify_api_key:
        print("❌ DIFY_API_KEY is not set!")
        return False
    
    headers = {
        "Authorization": f"Bearer {dify_api_key}",
        "Content-Type": "application/json"
    }
    
    # Test basic API connectivity
    print("1. Testing basic API connectivity...")
    try:
        response = requests.get(f"{dify_base_url}/info", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ API is accessible")
            app_info = response.json()
            print(f"   App Name: {app_info.get('name', 'Unknown')}")
        else:
            print(f"   ❌ API error: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False
    
    # Test file upload endpoints
    print("\n2. Testing file upload endpoints...")
    upload_endpoints = [
        f"{dify_base_url}/files/upload",
        f"{dify_base_url}/upload",
        f"{dify_base_url}/v1/files/upload",
        f"{dify_base_url}/v1/upload"
    ]
    
    working_endpoints = []
    for endpoint in upload_endpoints:
        try:
            # Try HEAD request first
            response = requests.head(endpoint, headers=headers, timeout=5)
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code in [200, 405]:  # 405 means method not allowed but endpoint exists
                working_endpoints.append(endpoint)
                print(f"   ✅ Endpoint exists")
            else:
                print(f"   ❌ Endpoint not available")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    if not working_endpoints:
        print("\n❌ No file upload endpoints found!")
        print("\n🔧 Possible solutions:")
        print("1. Check if your Dify instance supports file uploads")
        print("2. Verify the DIFY_BASE_URL is correct")
        print("3. Check if file upload is enabled in Dify configuration")
        print("4. Try using a different Dify instance or version")
        return False
    
    print(f"\n✅ Found working endpoints: {working_endpoints}")
    
    # Test actual file upload with a small test file
    print("\n3. Testing actual file upload...")
    test_content = b"Test file content for debugging"
    test_filename = "test.txt"
    
    file_url = None
    for endpoint in working_endpoints:
        try:
            files = {
                'file': (test_filename, test_content, 'text/plain'),
                'user': (None, 'test_user')
            }
            
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {dify_api_key}"},
                files=files,
                timeout=10
            )
            
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code in [200, 201]:  # 201 = Created
                print("   ✅ File upload successful!")
                result = response.json()
                print(f"   Response: {result}")
                
                # Extract file URL
                file_url = result.get('url') or result.get('file_url') or result.get('download_url') or result.get('preview_url')
                if file_url:
                    print(f"   File URL: {file_url}")
                    break
                else:
                    # Try to construct URL from file ID
                    file_id = result.get('id')
                    if file_id:
                        constructed_url = f"{dify_base_url}/files/{file_id}/download"
                        print(f"   Constructed File URL: {constructed_url}")
                        file_url = constructed_url
                        break
                    else:
                        print("   ⚠️ No file URL or ID found in response")
            else:
                print(f"   ❌ Upload failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Upload error: {e}")
    
    if not file_url:
        print("\n❌ All file upload attempts failed!")
        return False
    
    # Test sending message with file
    print("\n4. Testing message with file...")
    try:
        message_data = {
            "inputs": {},
            "query": "What is this file about?",
            "response_mode": "blocking",
            "conversation_id": "",
            "user": "test_user",
            "files": [
                {
                    "type": "document",
                    "transfer_method": "remote_url",
                    "url": file_url
                }
            ]
        }
        
        response = requests.post(
            f"{dify_base_url}/chat-messages",
            headers=headers,
            json=message_data,
            timeout=30
        )
        
        print(f"   Message with file: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Message with file successful!")
            result = response.json()
            print(f"   Answer: {result.get('answer', 'No answer')[:200]}...")
            return True
        else:
            print(f"   ❌ Message failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Message error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Dify API Debug Tool")
    print("=" * 50)
    
    success = check_dify_api()
    
    if success:
        print("\n🎉 Dify API file upload is working correctly!")
    else:
        print("\n💡 Next steps:")
        print("1. Check your Dify instance configuration")
        print("2. Verify file upload is enabled in Dify")
        print("3. Contact your Dify administrator")
        print("4. Consider using a different Dify instance")
