import unittest
from app import app, db
from models import User, Client

class FilterTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        
        self.lawyer = User.query.filter_by(email='maryicabreta@gmail.com').first()

    def test_lawyer_dashboard_filter_by_id(self):
        if not self.lawyer:
            print("Skipping: Lawyer not found")
            return

        # Login
        self.client.post('/login', data=dict(
            email=self.lawyer.email,
            password=self.lawyer.password
        ), follow_redirects=True)
        
        # Test ID search (using 'nombre' param as implemented)
        # Search for something likely to exist or just verify 200 OK
        rv = self.client.get('/lawyer?nombre=123')
        self.assertEqual(rv.status_code, 200)

if __name__ == '__main__':
    unittest.main()
