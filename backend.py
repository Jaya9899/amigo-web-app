from flask import Flask, request, jsonify
from flask_cors import CORS
from ai_pipeline.pipeline import DoubtPipeline
import time

SESSION_ID = int(time.time())
SESSION_FILE = f"filtered_doubts_session_{SESSION_ID}.txt"

app = Flask(__name__)
CORS(app)

pipelines = {}

def get_pipeline(course_id):
    if course_id not in pipelines:
        print(f"--- Initializing new pipeline for Course ID: {course_id} ---")
        pipelines[course_id] = DoubtPipeline()
        # Default topic if none set yet
        pipelines[course_id].set_topic("A general academic subject")
    return pipelines[course_id]

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "Amigo AI Backend is running!", "session_id": SESSION_ID, "active_courses": list(pipelines.keys())})

@app.route('/set_topic', methods=['POST'])
def set_topic():
    data = request.json
    if not data or "topic" not in data:
        print("Error: /set_topic called without topic")
        return jsonify({"error": "No topic provided"}), 400
    
    topic = data.get("topic")
    course_id = data.get("course_id", "default")
    print(f"--- Setting Topic for {course_id} to: \"{topic}\" ---")
    p = get_pipeline(course_id)
    p.set_topic(topic)
    return jsonify({"success": True, "topic": topic, "course_id": course_id})

@app.route('/submit_doubts', methods=['GET', 'POST'], strict_slashes=False)
@app.route('/submit_doubt', methods=['GET', 'POST'], strict_slashes=False)
def submit():
    if request.method == 'GET':
        return jsonify({"message": "Endpoint is active. Use POST to submit doubts."})
    
    print(f"\nReceived doubt submission request: {request.method} {request.path}")
    data = request.json
    if not data:
        print("Error: No JSON data in request")
        return jsonify({"error": "No JSON data provided"}), 400
        
    course_id = data.get("course_id", "default")
    p = get_pipeline(course_id)

    # Optional: set topic if passed with the doubt
    incoming_topic = data.get("topic")
    if incoming_topic:
        print(f"Updating topic for {course_id} from submission: \"{incoming_topic}\"")
        p.set_topic(incoming_topic)
    else:
        print(f"No topic in submission. Current pipeline topic for {course_id} is: \"{p._topic_filter._topic_text}\"")

    text = data.get("doubt", "")
    file_url = data.get("file_url")
    link = data.get("link")
    
    if not text:
        print("Error: No doubt text in JSON")
        return jsonify({"error": "No doubt text provided"}), 400
        
    print(f"Processing doubt for {course_id}: \"{text}\" (file: {file_url}, link: {link})")
    result = p.submit_doubt(text, file_url=file_url, link=link)
    print(f"Submission Result: Accepted={result.accepted}, Reason={result.rejection_reason}")
    
    # After submission, get the clustered summary to dump to file (session file logic kept for debug)
    output = p.get_clustered_summary()
    
    try:
        with open(SESSION_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n--- Course: {course_id} ---\n")
            f.write(f"Total Accepted: {output.total_accepted}\n")
            f.write(f"Total Rejected: {output.total_rejected}\n\n")
            
            f.write("--- ACCEPTED DOUBTS CLUSTERS ---\n")
            for c in output.clusters:
                f.write(f"Cluster {c.cluster_id} ({c.count} doubts) Summary: {c.summary}\n")
                for d in c.doubts:
                    f.write(f" - {d['text']} (file: {d['file_url']}, link: {d['link']})\n")
                f.write("\n")
                
            f.write("--- UNCLUSTERED ---\n")
            for u in output.unclustered:
                f.write(f" - {u['text']} (file: {u['file_url']}, link: {u['link']})\n")
    except Exception as e:
        print(f"Error writing to session file: {e}")
            
    return jsonify({
        "success": True,
        "accepted": result.accepted,
        "reason": result.rejection_reason
    })

@app.route('/get_doubts', methods=['GET'])
def get_all_doubts():
    course_id = request.args.get("course_id", "default")
    p = get_pipeline(course_id)

    # Get all submissions (including rejected ones)
    submissions = []
    for sub in p._submissions:
        submissions.append({
            "text": sub.text,
            "accepted": sub.accepted,
            "rejection_reason": sub.rejection_reason,
            "file_url": sub.file_url,
            "link": sub.link
        })
    
    # Get the latest clustered summary
    summary_output = p.get_clustered_summary()
    clusters = []
    for c in summary_output.clusters:
        clusters.append({
            "cluster_id": c.cluster_id,
            "summary": c.summary,
            "count": c.count,
            "doubts": c.doubts
        })

    return jsonify({
        "success": True,
        "course_id": course_id,
        "submissions": submissions,
        "clusters": clusters,
        "unclustered": summary_output.unclustered,
        "total_accepted": summary_output.total_accepted,
        "total_rejected": summary_output.total_rejected
    })

@app.route('/resolve_doubt', methods=['POST'])
def resolve_doubt():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    
    course_id = data.get("course_id", "default")
    doubt_text = data.get("doubt_text")
    res_text = data.get("resolution_text")
    res_file = data.get("resolution_file")
    res_audio = data.get("resolution_audio")
    
    if not doubt_text:
        return jsonify({"error": "Missing doubt_text"}), 400
        
    p = get_pipeline(course_id)
    success = p.resolve_doubt(doubt_text, res_text, res_file, res_audio)
    
    return jsonify({"success": success})


@app.errorhandler(404)
def page_not_found(e):
    print(f"404 Error: {request.method} {request.path}")
    return jsonify({"error": "Route not found", "path": request.path}), 404

if __name__ == '__main__':
    print("Starting Amigo AI Backend on http://localhost:5001")
    app.run(port=5001, debug=True, use_reloader=False)
