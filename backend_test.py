#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class VideoMarketplaceAPITester:
    def __init__(self, base_url="https://determined-cori-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.tests_run = 0
        self.tests_passed = 0
        self.user_token = None
        self.admin_token = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        if details:
            print(f"   Details: {details}")

    def test_root_endpoint(self):
        """Test root API endpoint"""
        try:
            response = self.session.get(f"{self.api_url}/")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Message: {data.get('message', 'N/A')}"
            self.log_test("Root Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("Root Endpoint", False, str(e))
            return False

    def test_seed_data(self):
        """Test seeding initial data"""
        try:
            response = self.session.post(f"{self.api_url}/seed-data")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Users: {data.get('users', 0)}, Videos: {data.get('videos', 0)}"
            self.log_test("Seed Data", success, details)
            return success
        except Exception as e:
            self.log_test("Seed Data", False, str(e))
            return False

    def test_user_registration(self):
        """Test user registration"""
        try:
            test_user = {
                "name": "Test User Registration",
                "email": f"testuser_{datetime.now().strftime('%H%M%S')}@test.com",
                "password": "TestPass123!"
            }
            
            response = self.session.post(f"{self.api_url}/auth/register", json=test_user)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", User ID: {data.get('id', 'N/A')}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("User Registration", success, details)
            return success
        except Exception as e:
            self.log_test("User Registration", False, str(e))
            return False

    def test_user_login(self):
        """Test user login with test credentials"""
        try:
            credentials = {
                "email": "test@test.com",
                "password": "test123"
            }
            
            response = self.session.post(f"{self.api_url}/auth/login", json=credentials)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", User: {data.get('user', {}).get('email', 'N/A')}"
                # Store cookies for subsequent requests
                self.user_token = True  # Using cookies, not token
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("User Login (test@test.com)", success, details)
            return success
        except Exception as e:
            self.log_test("User Login (test@test.com)", False, str(e))
            return False

    def test_admin_login(self):
        """Test admin login"""
        try:
            credentials = {
                "email": "admin@company.com",
                "password": "Admin@123"
            }
            
            response = self.session.post(f"{self.api_url}/auth/login", json=credentials)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Admin: {data.get('user', {}).get('email', 'N/A')}"
                self.admin_token = True  # Using cookies, not token
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("Admin Login (admin@company.com)", success, details)
            return success
        except Exception as e:
            self.log_test("Admin Login (admin@company.com)", False, str(e))
            return False

    def test_get_current_user(self):
        """Test getting current user info"""
        try:
            response = self.session.get(f"{self.api_url}/auth/me")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", User: {data.get('email', 'N/A')}, Role: {data.get('role', 'N/A')}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("Get Current User", success, details)
            return success
        except Exception as e:
            self.log_test("Get Current User", False, str(e))
            return False

    def test_get_videos(self):
        """Test getting all videos"""
        try:
            response = self.session.get(f"{self.api_url}/videos")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Videos count: {len(data)}"
                if len(data) > 0:
                    details += f", First video: {data[0].get('title', 'N/A')}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("Get All Videos", success, details)
            return success, data if success else []
        except Exception as e:
            self.log_test("Get All Videos", False, str(e))
            return False, []

    def test_get_video_by_id(self, video_id):
        """Test getting a specific video by ID"""
        try:
            response = self.session.get(f"{self.api_url}/videos/{video_id}")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Video: {data.get('title', 'N/A')}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("Get Video by ID", success, details)
            return success
        except Exception as e:
            self.log_test("Get Video by ID", False, str(e))
            return False

    def test_get_categories(self):
        """Test getting categories"""
        try:
            response = self.session.get(f"{self.api_url}/categories")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Categories count: {len(data)}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("Get Categories", success, details)
            return success
        except Exception as e:
            self.log_test("Get Categories", False, str(e))
            return False

    def test_get_lines_of_business(self):
        """Test getting lines of business"""
        try:
            response = self.session.get(f"{self.api_url}/lines-of-business")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", LOBs count: {len(data)}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_test("Get Lines of Business", success, details)
            return success
        except Exception as e:
            self.log_test("Get Lines of Business", False, str(e))
            return False

    def test_logout(self):
        """Test user logout"""
        try:
            response = self.session.post(f"{self.api_url}/auth/logout")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Message: {data.get('message', 'N/A')}"
            
            self.log_test("User Logout", success, details)
            return success
        except Exception as e:
            self.log_test("User Logout", False, str(e))
            return False

    def test_protected_route_without_auth(self):
        """Test accessing protected route without authentication"""
        # Create a new session without cookies
        temp_session = requests.Session()
        temp_session.headers.update({'Content-Type': 'application/json'})
        
        try:
            response = temp_session.get(f"{self.api_url}/videos")
            success = response.status_code == 401
            details = f"Status: {response.status_code} (Expected 401)"
            
            self.log_test("Protected Route Without Auth", success, details)
            return success
        except Exception as e:
            self.log_test("Protected Route Without Auth", False, str(e))
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Video Marketplace API Tests")
        print("=" * 50)
        
        # Test basic connectivity
        if not self.test_root_endpoint():
            print("❌ Cannot connect to API. Stopping tests.")
            return False
        
        # Seed data first
        self.test_seed_data()
        
        # Test authentication without login
        self.test_protected_route_without_auth()
        
        # Test user registration
        self.test_user_registration()
        
        # Test user login
        if not self.test_user_login():
            print("❌ User login failed. Cannot continue with authenticated tests.")
            return False
        
        # Test authenticated endpoints
        self.test_get_current_user()
        
        # Test video endpoints
        videos_success, videos_data = self.test_get_videos()
        
        if videos_success and videos_data:
            # Test getting a specific video
            first_video_id = videos_data[0].get('id')
            if first_video_id:
                self.test_get_video_by_id(first_video_id)
        
        # Test metadata endpoints
        self.test_get_categories()
        self.test_get_lines_of_business()
        
        # Test admin login
        self.test_admin_login()
        
        # Test logout
        self.test_logout()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    """Main test runner"""
    tester = VideoMarketplaceAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())