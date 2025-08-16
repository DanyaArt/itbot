import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = '127.0.0.1'
PORT = 8001
BASE_DIR = os.path.abspath(os.getcwd())
DB_PATH = os.path.join(BASE_DIR, 'database', 'bot_new.db')
OUT_JSON = os.path.join(BASE_DIR, 'universities.json')

class Handler(BaseHTTPRequestHandler):
	def _set_headers(self, code=200):
		self.send_response(code)
		self.send_header('Content-Type', 'application/json; charset=utf-8')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		self.send_header('Access-Control-Allow-Headers', 'Content-Type')
		self.end_headers()

	def do_OPTIONS(self):
		self._set_headers(200)

	def do_POST(self):
		if self.path == '/sync':
			try:
				data = export_from_db()
				with open(OUT_JSON, 'w', encoding='utf-8') as f:
					json.dump(data, f, ensure_ascii=False, indent=2)
				self._set_headers(200)
				self.wfile.write(json.dumps({'status':'ok','count':len(data)}).encode('utf-8'))
			except Exception as e:
				self._set_headers(500)
				self.wfile.write(json.dumps({'status':'error','message':str(e)}).encode('utf-8'))
		else:
			self._set_headers(404)
			self.wfile.write(json.dumps({'error':'not found'}).encode('utf-8'))


def export_from_db():
	if not os.path.isfile(DB_PATH):
		return []
	conn = sqlite3.connect(DB_PATH)
	cur = conn.cursor()
	cur.execute(
		"""
		SELECT u.name, u.city, u.score_min, u.score_max, u.url, s.name as specialization
		FROM universities u
		LEFT JOIN specializations s ON s.id = u.specialization_id
		"""
	)
	rows = cur.fetchall()
	conn.close()
	result = []
	for name, city, smin, smax, url, spec in rows:
		result.append({
			'name': name,
			'city': city,
			'score_min': smin,
			'score_max': smax,
			'url': url,
			'specialization': spec,
		})
	return result

if __name__ == '__main__':
	server = HTTPServer((HOST, PORT), Handler)
	print(f"Sync server started on http://{HOST}:{PORT}")
	print(f"DB: {DB_PATH}")
	print(f"Output: {OUT_JSON}")
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		pass
	server.server_close()
	print("Stopped") 