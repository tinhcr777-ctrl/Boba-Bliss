"""Run: python -m unittest discover -s tests -v (after installing requirements)."""
import os
import tempfile
import unittest
from app import create_app

class BobaBlissTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": os.path.join(self.temp.name, "test.db"), "SECRET_KEY": "test-only-secret"})
        self.client = self.app.test_client()
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()

    def tearDown(self):
        self.app_ctx.pop()
        self.temp.cleanup()

    def token(self):
        self.client.get("/")
        with self.client.session_transaction() as sess:
            return sess["csrf_token"]

    def test_public_pages(self):
        for page in ["/", "/menu", "/preview", "/contact"]:
            self.assertEqual(self.client.get(page).status_code, 200)
        self.assertIn(b"Brown Sugar Milk Tea", self.client.get('/menu').data)

    def test_admin_requires_login(self):
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login', response.location)

    def test_csrf_rejects_invalid_post(self):
        self.assertEqual(self.client.post('/admin/login', data={'username':'a','password':'x'}).status_code, 400)

    def test_order_and_admin_crud(self):
        from werkzeug.security import generate_password_hash
        # Use a direct sqlite connection for fixture user creation.
        import sqlite3
        with sqlite3.connect(self.app.config['DATABASE']) as dbconn:
            dbconn.execute('INSERT INTO admins(username,password_hash) VALUES (?,?)', ('teacher',generate_password_hash('securepassword')))
        form = dict(csrf_token=self.token(),customer_name='Demo Student',phone='555-0100',size='Large',sweetness='50%',quantity='2',notes='light ice')
        res = self.client.post('/order/1', data=form)
        self.assertEqual(res.status_code,302)
        self.assertIn('/order-success/',res.location)
        response = self.client.post('/admin/login',data={'csrf_token':self.token(),'username':'teacher','password':'securepassword'})
        self.assertEqual(response.status_code,302)
        self.assertIn(b'Demo Student',self.client.get('/admin').data)
        res = self.client.post('/admin/drinks/new',data={'csrf_token':self.token(),'name':'Taro Cream','description':'Yum','price':'5.25','emoji':'🧋','sort_order':'5','available':'on'})
        self.assertEqual(res.status_code,302)
        self.assertIn(b'Taro Cream',self.client.get('/menu').data)
        import sqlite3
        with sqlite3.connect(self.app.config['DATABASE']) as dbconn:
            drink_id = dbconn.execute("SELECT id FROM drinks WHERE name='Taro Cream'").fetchone()[0]
        res = self.client.post(f'/admin/drinks/{drink_id}/delete',data={'csrf_token':self.token()})
        self.assertEqual(res.status_code,302)
        self.assertNotIn(b'Taro Cream',self.client.get('/menu').data)

if __name__ == '__main__':
    unittest.main()
