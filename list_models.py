#!/usr/bin/env python3
"""List available Gemini models"""
import os
from google import genai

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ GOOGLE_API_KEY not set")
    exit(1)

client = genai.Client(api_key=api_key)

print("🔍 Listing available Gemini models...\n")

try:
    models = client.models.list()
    
    print("Available models for generateContent:")
    print("=" * 60)
    
    for model in models:
        # Check if model supports generateContent
        if hasattr(model, 'supported_generation_methods'):
            methods = model.supported_generation_methods
        else:
            methods = ['generateContent']  # Assume support
            
        if 'generateContent' in methods:
            print(f"✅ {model.name}")
            if hasattr(model, 'display_name'):
                print(f"   Display: {model.display_name}")
            if hasattr(model, 'description'):
                print(f"   Desc: {model.description[:100]}...")
            print()
    
except Exception as e:
    print(f"❌ Error listing models: {e}")
    print(f"\nTrying alternate approach...")
    
    # Try common model names
    test_models = [
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro",
    ]
    
    print("\nTesting model availability:")
    for model_name in test_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="test"
            )
            print(f"✅ {model_name} - WORKS")
        except Exception as e:
            print(f"❌ {model_name} - {str(e)[:80]}")
