#!/usr/bin/env python3
"""
Test script to check file type detection
"""
import sys
import os
import mimetypes

def get_file_type_from_filename(filename: str) -> str:
    """Get Dify file type based on file extension."""
    content_type, _ = mimetypes.guess_type(filename)
    
    print(f"Determining file type for {filename}: content_type={content_type}")
    
    if content_type:
        if content_type.startswith('image/'):
            print(f"File type determined as: image")
            return 'image'
        elif content_type in ['text/plain', 'text/markdown', 'application/pdf',
                            'text/html', 'application/vnd.ms-excel',
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            'application/msword',
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            'text/csv', 'application/xml', 'application/epub+zip']:
            print(f"File type determined as: document")
            return 'document'
        elif content_type.startswith('audio/'):
            print(f"File type determined as: audio")
            return 'audio'
        elif content_type.startswith('video/'):
            print(f"File type determined as: video")
            return 'video'
    
    # Fallback based on file extension
    ext = filename.lower().split('.')[-1]
    if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg']:
        print(f"File type determined as: image (by extension)")
        return 'image'
    elif ext in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
        print(f"File type determined as: audio (by extension)")
        return 'audio'
    elif ext in ['mp4', 'avi', 'mov', 'wmv', 'mkv']:
        print(f"File type determined as: video (by extension)")
        return 'video'
    else:
        print(f"File type determined as: document (default)")
        return 'document'

def test_file_type_detection():
    """Test file type detection for various file types."""
    
    test_files = [
        "test.png",
        "test.jpg", 
        "test.jpeg",
        "test.gif",
        "test.webp",
        "test.pdf",
        "test.txt",
        "test.docx",
        "test.mp3",
        "test.mp4"
    ]
    
    print("🔍 Testing file type detection:")
    print("-" * 50)
    
    for filename in test_files:
        print(f"\n--- Testing {filename} ---")
        file_type = get_file_type_from_filename(filename)
        print(f"Result: {filename:15} -> {file_type}")
    
    print("\n" + "="*50)
    print("🔍 Testing with actual PNG filename:")
    png_filename = "Screenshot 2025-09-16 at 11.53.23 PM.png"
    print(f"\n--- Testing {png_filename} ---")
    file_type = get_file_type_from_filename(png_filename)
    print(f"Result: {png_filename} -> {file_type}")
    
    print("\n" + "="*50)
    print("📋 Dify API File Format:")
    print("Files array should look like:")
    print("[")
    print("  {")
    print(f"    'type': '{file_type}',")
    print("    'transfer_method': 'local_file',")
    print("    'upload_file_id': 'file-id-from-upload'")
    print("  }")
    print("]")

if __name__ == "__main__":
    test_file_type_detection()
