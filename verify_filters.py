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

    def login(self, email, password):
        return self.client.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def test_lawyer_dashboard_filter(self):
        if not self.lawyer:
            print("Skipping: Lawyer not found")
            return

        self.login(self.lawyer.email, self.lawyer.password)
        
        # 1. Basic load
        rv = self.client.get('/lawyer')
        self.assertEqual(rv.status_code, 200)
        # Check for form label
        self.assertIn(b'Filtros de B', rv.data)

        # 2. Filter by Name
        rv = self.client.get('/lawyer?nombre=Juan')
        self.assertEqual(rv.status_code, 200)

        # 3. Filter by Analyst
        rv = self.client.get('/lawyer?analista=Pedro')
        self.assertEqual(rv.status_code, 200)
        
        # 4. Filter by Date
        rv = self.client.get('/lawyer?fecha=2024-01-01')
        self.assertEqual(rv.status_code, 200)

if __name__ == '__main__':
    unittest.main()
