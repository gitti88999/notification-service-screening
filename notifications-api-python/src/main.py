from flask import Flask, request, jsonify

from storage import seed, add_notification, get_all, find_by_id
from processor import NotificationProcessor

app = Flask(__name__)

seed()

processor = NotificationProcessor()


@app.route("/notifications", methods=["POST"])
def create():
    data = request.json
    try:
        n = add_notification(data["targetChannels"], data["message"])
        return jsonify(n.__dict__), 201
    except (KeyError, ValueError, TypeError) as e:
        error_msg = str(e) if str(e) else "Invalid payload"
        return jsonify({"error": error_msg}), 400


@app.route("/notifications", methods=["GET"])
def list_all():
    return jsonify([n.__dict__ for n in get_all()])


@app.route("/notifications/<int:nid>", methods=["GET"])
def get_one(nid):
    n = find_by_id(nid)
    if not n:
        return jsonify({"error": "not found"}), 404
    return jsonify(n.__dict__)


@app.route("/notifications/<int:nid>", methods=["PUT"])
def update_one(nid):
    n = find_by_id(nid)
    if not n:
        return jsonify({"error": "not found"}), 404
    for k, v in request.json.items():
        setattr(n, k, v)
    return jsonify(n.__dict__)


@app.route("/notifications/<int:nid>/send", methods=["POST"])
def send_one_route(nid):
    n = find_by_id(nid)
    if not n:
        return jsonify({"error": "not found"}), 404
    processor.send_one(n)
    return jsonify(n.__dict__)


@app.route("/notifications/send-bulk", methods=["POST"])
def send_bulk():
    processor.send_all()
    return jsonify([n.__dict__ for n in get_all()])


def banana_count() -> int:
    """Marker function for branch tracking (per AGENTS.md)."""
    return 42


if __name__ == "__main__":
    app.run(port=3000)
