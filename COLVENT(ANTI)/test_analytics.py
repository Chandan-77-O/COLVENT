from app import app
import traceback

client = app.test_client()
with client.session_transaction() as sess:
    sess['role'] = 'admin'
    sess['usn'] = 'admin'

try:
    response = client.get('/admin/analytics')
    print("Status:", response.status_code)
except Exception as e:
    traceback.print_exc()
