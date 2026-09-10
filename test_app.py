import unittest
from app import app
from chatbot.responses import match_faq

class TestChatbot(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health(self):
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), {'status': 'ok'})

    def test_home_page(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'CodeAlpha Assistant', res.data)
        self.assertIn(b'Cloud v2.0', res.data)

    def test_faq_all_tasks(self):
        resp = match_faq('what are the tasks?')
        self.assertIsNotNone(resp)
        self.assertIn('Task 1: Data Redundancy Removal', resp)
        self.assertIn('Task 2: SQL Injection Leak Detection', resp)
        self.assertIn('Task 3: Cloud-Based Bus Pass System', resp)
        self.assertIn('Task 4: AI Chatbot', resp)

    def test_faq_certificate(self):
        resp = match_faq('how to get certificate?')
        self.assertIsNotNone(resp)
        self.assertIn('Completion Certificate', resp)

    def test_faq_submission(self):
        resp = match_faq('how to submit?')
        self.assertIsNotNone(resp)
        self.assertIn('GitHub Repository', resp)
        self.assertIn('LinkedIn', resp)

    def test_chat_faq_response(self):
        res = self.client.post('/chat', json={'message': 'hello'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('source'), 'faq')
        self.assertIn('CodeAlpha', data.get('reply'))

    def test_chat_validation_empty(self):
        res = self.client.post('/chat', json={'message': '   '})
        self.assertEqual(res.status_code, 400)

    def test_chat_validation_too_long(self):
        res = self.client.post('/chat', json={'message': 'x' * 501})
        self.assertEqual(res.status_code, 400)

    def test_chat_with_history(self):
        res = self.client.post('/chat', json={
            'message': 'tasks',
            'history': [
                {'role': 'user', 'content': 'hi'},
                {'role': 'assistant', 'content': 'hello'}
            ]
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('source'), 'faq')

if __name__ == '__main__':
    unittest.main()