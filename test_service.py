"""
Test script for Platform Services
"""
import asyncio
import httpx
import json
from datetime import datetime


async def test_platform_services():
    """Test the unified platform services."""
    base_url = "http://localhost:8007"
    
    async with httpx.AsyncClient() as client:
        print("🚀 Testing Platform Services")
        print("=" * 50)
        
        # Test health endpoint
        print("1. Testing health check...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print()
        
        # Test service info
        print("2. Testing service info...")
        try:
            response = await client.get(f"{base_url}/")
            print(f"   Status: {response.status_code}")
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Uptime: {data.get('uptime_seconds', 0):.2f}s")
        except Exception as e:
            print(f"   Error: {e}")
        
        print()
        
        # Test auth endpoints
        print("3. Testing Auth Service...")
        test_user = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        
        # Register user
        print("   3a. Registering user...")
        try:
            response = await client.post(f"{base_url}/auth/register", json=test_user)
            print(f"   Status: {response.status_code}")
            if response.status_code == 201:
                token_data = response.json()
                token = token_data["access_token"]
                print(f"   Token received: {token[:20]}...")
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
            token = None
        
        # Login user
        print("   3b. Logging in user...")
        try:
            response = await client.post(f"{base_url}/auth/login", json=test_user)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                token_data = response.json()
                token = token_data["access_token"]
                print(f"   Token received: {token[:20]}...")
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
            token = None
        
        # Verify token
        if token:
            print("   3c. Verifying token...")
            try:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(f"{base_url}/auth/verify", headers=headers)
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    user_data = response.json()
                    print(f"   User: {user_data}")
            except Exception as e:
                print(f"   Error: {e}")
        
        print()
        
        # Test analytics endpoints
        print("4. Testing Analytics Service...")
        
        # Record some test metrics
        print("   4a. Recording test metrics...")
        test_metrics = [
            {
                "type": "api_call",
                "value": 1.0,
                "user_id": "test_user_1",
                "metadata": {"endpoint": "/test", "method": "GET"}
            },
            {
                "type": "cost",
                "value": 0.05,
                "user_id": "test_user_1",
                "metadata": {"service": "openai", "model": "gpt-4"}
            },
            {
                "type": "session",
                "value": 300.0,
                "user_id": "test_user_1",
                "metadata": {"session_id": "session_123"}
            }
        ]
        
        for metric in test_metrics:
            try:
                response = await client.post(f"{base_url}/analytics/events", json=metric)
                print(f"   Metric {metric['type']}: {response.status_code}")
            except Exception as e:
                print(f"   Error recording {metric['type']}: {e}")
        
        # Wait a bit for async processing
        await asyncio.sleep(1)
        
        # Get system metrics
        print("   4b. Getting system metrics...")
        try:
            response = await client.get(f"{base_url}/analytics/metrics")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                metrics = response.json()
                print(f"   Total metrics: {metrics.get('total_metrics', 0)}")
                print(f"   Active users: {metrics.get('active_users', 0)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Get user stats
        print("   4c. Getting user statistics...")
        try:
            response = await client.get(f"{base_url}/analytics/usage/test_user_1")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                stats = response.json()
                print(f"   API calls: {stats.get('api_calls', 0)}")
                print(f"   Total cost: ${stats.get('total_cost', 0):.4f}")
                print(f"   Sessions: {stats.get('sessions', 0)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print()
        
        # Test legacy endpoints
        print("5. Testing Legacy Endpoints...")
        
        print("   5a. Legacy metrics...")
        try:
            response = await client.get(f"{base_url}/metrics")
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print("   5b. Legacy usage...")
        try:
            response = await client.get(f"{base_url}/usage/test_user_1")
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print()
        print("🎉 Platform Services Test Complete!")


if __name__ == "__main__":
    print("Starting Platform Services tests...")
    print("Make sure the service is running on http://localhost:8007")
    print()
    
    try:
        asyncio.run(test_platform_services())
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")