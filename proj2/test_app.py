#!/usr/bin/env python3
"""
Comprehensive test suite for the Weeklies meal recommendation app
Tests all restaurant search, menu viewing, cart management, and ordering functionality
"""

import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app and database helpers
from Flask_app import app, create_connection, close_connection, fetch_one, fetch_all, execute_query
from sqlQueries import create_connection as sql_create_connection

class TestWeekliesApp(unittest.TestCase):
    """Test suite for the Weeklies meal recommendation app"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Test database file
        self.test_db = os.path.join(os.path.dirname(__file__), 'test_CSC510_DB.db')
        
        # Sample test data
        self.sample_restaurant = {
            'rtr_id': 1,
            'name': 'Test Restaurant',
            'description': 'Italian Cuisine',
            'address': '123 Test St',
            'city': 'Test City',
            'state': 'TS',
            'zip': '12345',
            'phone': '555-0123',
            'hours': '9AM-9PM',
            'status': 'Open'
        }
        
        self.sample_menu_item = {
            'itm_id': 1,
            'rtr_id': 1,
            'name': 'Test Pizza',
            'description': 'Delicious test pizza',
            'price': 1500,  # $15.00 in cents
            'calories': 500,
            'allergens': 'Gluten, Dairy',
            'instock': 1
        }
        
        self.sample_user = {
            'usr_id': 1,
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'phone': '555-0123',
            'password_HS': 'hashed_password',
            'wallet': 5000,  # $50.00 in cents
            'preferences': 'Italian, Vegetarian',
            'allergies': 'Nuts',
            'generated_menu': ''
        }

    def tearDown(self):
        """Clean up after tests"""
        # Remove test database if it exists
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_app_initialization(self):
        """Test that the Flask app initializes correctly"""
        self.assertIsNotNone(app)
        self.assertEqual(app.name, 'Flask_app')

    def test_database_connection(self):
        """Test database connection functionality"""
        # Test with main database
        conn = create_connection(os.path.join(os.path.dirname(__file__), 'CSC510_DB.db'))
        self.assertIsNotNone(conn)
        close_connection(conn)

    def test_restaurant_search_route(self):
        """Test restaurant search functionality"""
        # Test without authentication (should redirect to login)
        response = self.app.get('/restaurants')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_restaurant_search_with_auth(self):
        """Test restaurant search with authentication"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/restaurants')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Find Restaurants', response.data)

    def test_restaurant_search_filters(self):
        """Test restaurant search with various filters"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Test search query
        response = self.app.get('/restaurants?q=Italian')
        self.assertEqual(response.status_code, 200)

        # Test cuisine filter
        response = self.app.get('/restaurants?cuisine=Italian')
        self.assertEqual(response.status_code, 200)

        # Test location filter
        response = self.app.get('/restaurants?location=Test City')
        self.assertEqual(response.status_code, 200)

        # Test sorting
        response = self.app.get('/restaurants?sort=rating')
        self.assertEqual(response.status_code, 200)

    def test_restaurant_menu_route(self):
        """Test individual restaurant menu viewing"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Test with valid restaurant ID
        response = self.app.get('/restaurant/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Menu Items', response.data)

        # Test with invalid restaurant ID
        response = self.app.get('/restaurant/999')
        self.assertEqual(response.status_code, 302)  # Should redirect

    def test_orders_redirect(self):
        """Test that orders route redirects to restaurants"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/orders')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/restaurants', response.location)

    def test_order_placement_post(self):
        """Test order placement via POST request"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Sample order data
        order_data = {
            'restaurant_id': 1,
            'items': [
                {
                    'itm_id': 1,
                    'qty': 2,
                    'notes': 'Extra cheese'
                }
            ],
            'delivery_type': 'delivery',
            'tip': 2.50,
            'eta_minutes': 30,
            'date': '2025-01-01',
            'meal': 3
        }

        response = self.app.post('/order', 
                               data=json.dumps(order_data),
                               content_type='application/json')
        
        # Should return JSON response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('ok', data)

    def test_order_placement_get(self):
        """Test order placement via GET request (legacy support)"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Test with valid parameters
        response = self.app.get('/order?itm_id=1&qty=1&delivery=delivery&tip=2.50')
        self.assertEqual(response.status_code, 302)  # Should redirect to profile

    def test_profile_route(self):
        """Test user profile page"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/profile')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Profile', response.data)

    def test_edit_profile_route(self):
        """Test edit profile page"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/profile/edit')
        self.assertEqual(response.status_code, 200)

    def test_password_change(self):
        """Test password change functionality"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Test password change
        response = self.app.post('/profile/change-password', data={
            'current_password': 'old_password',
            'new_password': 'new_password',
            'confirm_password': 'new_password'
        })
        
        # Should redirect back to profile
        self.assertEqual(response.status_code, 302)

    def test_login_route(self):
        """Test login functionality"""
        # Test GET request
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

        # Test POST request with invalid credentials
        response = self.app.post('/login', data={
            'email': 'invalid@example.com',
            'password': 'wrong_password'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid credentials', response.data)

    def test_register_route(self):
        """Test registration functionality"""
        # Test GET request
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create your account', response.data)

        # Test POST request with valid data
        response = self.app.post('/register', data={
            'fname': 'New',
            'lname': 'User',
            'email': 'newuser@example.com',
            'phone': '555-9999',
            'password': 'password123',
            'confirm_password': 'password123',
            'allergies': 'Nuts',
            'preferences': 'Vegetarian'
        })
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_logout_route(self):
        """Test logout functionality"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'

        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_database_viewer(self):
        """Test database viewer functionality"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/db')
        self.assertEqual(response.status_code, 200)

        # Test with specific table
        response = self.app.get('/db?t=User')
        self.assertEqual(response.status_code, 200)

    def test_money_helper_functions(self):
        """Test helper functions for money calculations"""
        from Flask_app import _money, _cents_to_dollars
        
        # Test _money function
        self.assertEqual(_money(10.123), 10.12)
        self.assertEqual(_money(10.999), 11.00)
        self.assertEqual(_money(0), 0.0)
        
        # Test _cents_to_dollars function
        self.assertEqual(_cents_to_dollars(1500), 15.0)
        self.assertEqual(_cents_to_dollars(0), 0.0)
        self.assertEqual(_cents_to_dollars(123), 1.23)

    def test_parse_generated_menu(self):
        """Test generated menu parsing functionality"""
        from Flask_app import parse_generated_menu
        
        # Test valid menu string
        menu_str = "[2025-01-01,1,1][2025-01-01,2,2][2025-01-02,3,3]"
        result = parse_generated_menu(menu_str)
        
        self.assertIn('2025-01-01', result)
        self.assertIn('2025-01-02', result)
        self.assertEqual(len(result['2025-01-01']), 2)
        self.assertEqual(len(result['2025-01-02']), 1)

    def test_fetch_menu_items_by_ids(self):
        """Test menu item fetching by IDs"""
        from Flask_app import fetch_menu_items_by_ids
        
        # Test with empty list
        result = fetch_menu_items_by_ids([])
        self.assertEqual(result, {})
        
        # Test with non-existent IDs
        result = fetch_menu_items_by_ids([999, 998])
        self.assertEqual(result, {})

    def test_palette_for_item_ids(self):
        """Test color palette generation for menu items"""
        from Flask_app import palette_for_item_ids
        
        # Test with sample IDs
        item_ids = [1, 2, 3, 4, 5]
        palette = palette_for_item_ids(item_ids)
        
        self.assertEqual(len(palette), len(item_ids))
        for item_id in item_ids:
            self.assertIn(item_id, palette)
            self.assertTrue(palette[item_id].startswith('#'))

    def test_build_calendar_cells(self):
        """Test calendar cell building functionality"""
        from Flask_app import build_calendar_cells
        
        # Test with sample data
        gen_map = {
            '2025-01-01': [{'itm_id': 1, 'meal': 1}],
            '2025-01-02': [{'itm_id': 2, 'meal': 2}]
        }
        items_by_id = {
            1: {'itm_id': 1, 'name': 'Breakfast', 'restaurant_name': 'Test'},
            2: {'itm_id': 2, 'name': 'Lunch', 'restaurant_name': 'Test'}
        }
        
        cells = build_calendar_cells(gen_map, 2025, 1, items_by_id)
        self.assertIsInstance(cells, list)
        self.assertGreater(len(cells), 0)

    def test_authentication_required(self):
        """Test that authentication is required for protected routes"""
        protected_routes = [
            '/',
            '/profile',
            '/profile/edit',
            '/restaurants',
            '/restaurant/1',
            '/orders',
            '/db'
        ]
        
        for route in protected_routes:
            response = self.app.get(route)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)

    def test_session_management(self):
        """Test session management functionality"""
        # Test login creates session
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

        # Test logout clears session
        response = self.app.get('/logout')
        self.assertEqual(response.status_code, 302)

    def test_error_handling(self):
        """Test error handling for various scenarios"""
        # Test 404 for non-existent routes
        response = self.app.get('/nonexistent')
        self.assertEqual(response.status_code, 404)

        # Test invalid restaurant ID
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/restaurant/invalid')
        self.assertEqual(response.status_code, 404)

    def test_json_response_format(self):
        """Test that JSON responses are properly formatted"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Test order placement JSON response
        order_data = {
            'restaurant_id': 1,
            'items': [{'itm_id': 1, 'qty': 1, 'notes': ''}],
            'delivery_type': 'delivery',
            'tip': 0,
            'eta_minutes': 40,
            'date': '2025-01-01',
            'meal': 3
        }

        response = self.app.post('/order', 
                               data=json.dumps(order_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('ok', data)

    def test_template_rendering(self):
        """Test that templates render without errors"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Test main templates
        templates_to_test = [
            ('/', 'Menu Calendar'),
            ('/restaurants', 'Find Restaurants'),
            ('/profile', 'Profile'),
            ('/profile/edit', 'Edit Profile')
        ]

        for route, expected_content in templates_to_test:
            response = self.app.get(route)
            self.assertEqual(response.status_code, 200)
            self.assertIn(expected_content.encode(), response.data)

    def test_cart_functionality_simulation(self):
        """Test cart functionality by simulating the JavaScript behavior"""
        # This test simulates what the JavaScript cart would do
        cart_data = {
            'restaurant_id': 1,
            'items': [
                {
                    'item_id': 1,
                    'name': 'Test Pizza',
                    'price': 15.00,
                    'quantity': 2,
                    'restaurant_name': 'Test Restaurant'
                }
            ]
        }
        
        # Simulate cart calculations
        subtotal = sum(item['price'] * item['quantity'] for item in cart_data['items'])
        tax = subtotal * 0.0725
        delivery_fee = 3.99
        service_fee = 1.49
        total = subtotal + tax + delivery_fee + service_fee
        
        self.assertEqual(subtotal, 30.00)
        self.assertEqual(tax, 2.175)
        self.assertEqual(total, 37.655)

    def test_restaurant_search_parameters(self):
        """Test restaurant search with various parameter combinations"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Test different search combinations
        search_params = [
            {'q': 'Italian'},
            {'cuisine': 'Pizza'},
            {'location': 'Downtown'},
            {'sort': 'rating'},
            {'q': 'Italian', 'cuisine': 'Pizza', 'location': 'Downtown', 'sort': 'rating'}
        ]

        for params in search_params:
            response = self.app.get('/restaurants', query_string=params)
            self.assertEqual(response.status_code, 200)

    def test_menu_item_display(self):
        """Test menu item display functionality"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/restaurant/1')
        self.assertEqual(response.status_code, 200)
        
        # Check that menu items are displayed
        self.assertIn(b'Menu Items', response.data)

    def test_responsive_design_elements(self):
        """Test that responsive design elements are present"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/restaurants')
        self.assertEqual(response.status_code, 200)
        
        # Check for responsive design elements
        self.assertIn(b'meta name="viewport"', response.data)
        self.assertIn(b'grid-template-columns', response.data)

    def test_accessibility_features(self):
        """Test accessibility features"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get('/restaurants')
        self.assertEqual(response.status_code, 200)
        
        # Check for accessibility features
        self.assertIn(b'aria-current', response.data)
        self.assertIn(b'aria-label', response.data)

    def test_security_features(self):
        """Test security features"""
        # Test SQL injection protection
        malicious_input = "'; DROP TABLE User; --"
        
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        response = self.app.get(f'/restaurants?q={malicious_input}')
        self.assertEqual(response.status_code, 200)
        # Should not cause any errors

    def test_performance_considerations(self):
        """Test performance-related functionality"""
        with self.app.session_transaction() as sess:
            sess['Username'] = 'Test User'
            sess['Email'] = 'test@example.com'
            sess['usr_id'] = 1

        # Test that pages load within reasonable time
        import time
        start_time = time.time()
        
        response = self.app.get('/restaurants')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 5.0)  # Should load within 5 seconds

def run_tests():
    """Run all tests and display results"""
    print("🧪 Running Weeklies App Test Suite")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestWeekliesApp)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
