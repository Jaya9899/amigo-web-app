from flask import Flask, request, jsonify
from flask_cors import CORS
from ai_pipeline.pipeline import DoubtPipeline
import time

SESSION_ID = int(time.time())
SESSION_FILE = f"filtered_doubts_session_{SESSION_ID}.txt"

app = Flask(__name__)
CORS(app)

# Seed data from seed-database.html
SEED_CLASSROOMS = [
    {
        "id": "cls_seed_001",
        "name": "Software Engineering",
        "code": "CS-402",
        "schedule": "Mon, Wed • 10:00 AM",
        "color": "sage",
        "icon": "💻",
        "facultyEmail": "dr.richards@nitw.ac.in",
        "facultyName": "Dr. Richards",
        "department": "Computer Science",
        "students": [
            {"rollNo": "22CS1001", "email": "ananya.k@student.nitw.ac.in"},
            {"rollNo": "22CS1002", "email": "rahul.s@student.nitw.ac.in"},
            {"rollNo": "22CS1003", "email": "sneha.p@student.nitw.ac.in"},
            {"rollNo": "22CS1004", "email": "divya.g@student.nitw.ac.in"}
        ]
    },
    {
        "id": "cls_seed_002",
        "name": "Database Management Systems",
        "code": "CS-301",
        "schedule": "Tue, Thu • 11:30 AM",
        "color": "sky",
        "icon": "📐",
        "facultyEmail": "prof.menon@nitw.ac.in",
        "facultyName": "Prof. Priya Menon",
        "department": "Computer Science",
        "students": [
            {"rollNo": "22CS1001", "email": "ananya.k@student.nitw.ac.in"},
            {"rollNo": "22CS1002", "email": "rahul.s@student.nitw.ac.in"},
            {"rollNo": "22EC1001", "email": "vikram.r@student.nitw.ac.in"},
            {"rollNo": "22CS1004", "email": "divya.g@student.nitw.ac.in"}
        ]
    },
    {
        "id": "cls_seed_003",
        "name": "Data Structures & Algorithms",
        "code": "CS-201",
        "schedule": "Mon, Wed, Fri • 2:00 PM",
        "color": "peach",
        "icon": "⚡",
        "facultyEmail": "dr.richards@nitw.ac.in",
        "facultyName": "Dr. Richards",
        "department": "Computer Science",
        "students": [
            {"rollNo": "22CS1001", "email": "ananya.k@student.nitw.ac.in"},
            {"rollNo": "22CS1003", "email": "sneha.p@student.nitw.ac.in"},
            {"rollNo": "22CS1004", "email": "divya.g@student.nitw.ac.in"}
        ]
    },
    {
        "id": "cls_seed_004",
        "name": "Signals & Systems",
        "code": "EC-301",
        "schedule": "Tue, Thu • 9:00 AM",
        "color": "mint",
        "icon": "📡",
        "facultyEmail": "dr.reddy@nitw.ac.in",
        "facultyName": "Dr. Kavitha Reddy",
        "department": "Electronics",
        "students": [
            {"rollNo": "22CS1002", "email": "rahul.s@student.nitw.ac.in"},
            {"rollNo": "22CS1003", "email": "sneha.p@student.nitw.ac.in"},
            {"rollNo": "22EC1001", "email": "vikram.r@student.nitw.ac.in"}
        ]
    }
]

pipelines = {}
active_sessions = set()
classrooms = list(SEED_CLASSROOMS) # Pre-populate with seed data
live_sessions = {} # Store detailed session info: {course_id: {topic, faculty}}

def get_pipeline(course_id):
    if course_id not in pipelines:
        print(f"--- Initializing new pipeline for Course ID: {course_id} ---")
        pipelines[course_id] = DoubtPipeline()
        # Default topic if none set yet
        pipelines[course_id].set_topic("A general academic subject")
    return pipelines[course_id]

@app.route('/')
def index():
    return jsonify({
        "status": "ok", 
        "message": "Amigo AI Backend is running!", 
        "session_id": SESSION_ID, 
        "active_courses": list(pipelines.keys()),
        "active_sessions": list(active_sessions),
        "classrooms_count": len(classrooms)
    })

@app.route('/add_classroom', methods=['POST'])
def add_classroom():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    classrooms.append(data)
    print(f"--- Classroom added: {data.get('name')} ({data.get('id')}) ---")
    return jsonify({"success": True})

@app.route('/get_classrooms', methods=['GET'])
def get_classrooms():
    return jsonify({"classrooms": classrooms})

@app.route('/start_session', methods=['POST'])
def start_session():
    data = request.json
    course_id = data.get("course_id", "default")
    topic = data.get("topic", "Class Session")
    faculty = data.get("faculty", "Faculty")
    
    # Use float timestamp for precise duration calculation
    start_time = time.time()
    
    active_sessions.add(course_id)
    live_sessions[course_id] = {
        "classId": course_id,
        "topic": topic,
        "facultyName": faculty,
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
        "startTime": start_time # Raw timestamp for duration
    }
    
    print(f"--- Session started for Course ID: {course_id} | Topic: {topic} ---")
    return jsonify({"success": True, "course_id": course_id, "startTime": start_time})

@app.route('/end_session', methods=['POST'])
def end_session():
    data = request.json
    course_id = data.get("course_id", "default")
    if course_id in active_sessions:
        active_sessions.remove(course_id)
    if course_id in live_sessions:
        del live_sessions[course_id]
    print(f"--- Session ended for Course ID: {course_id} ---")
    return jsonify({"success": True, "course_id": course_id})

@app.route('/is_session_active', methods=['GET'])
def is_session_active():
    course_id = request.args.get("course_id", "default")
    return jsonify({"active": course_id in active_sessions})

@app.route('/active_sessions', methods=['GET'])
def get_active_sessions():
    return jsonify({
        "active_sessions": list(active_sessions),
        "live_sessions": list(live_sessions.values())
    })

@app.route('/get_live_sessions', methods=['GET'])
def get_live_sessions():
    return jsonify({"live_sessions": list(live_sessions.values())})

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
    source = data.get("source", "live")
    
    if not text:
        print("Error: No doubt text in JSON")
        return jsonify({"error": "No doubt text provided"}), 400
        
    print(f"Processing doubt for {course_id}: \"{text}\" (source: {source}, file: {file_url}, link: {link})")
    result = p.submit_doubt(text, file_url=file_url, link=link, source=source)
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
    source_filter = request.args.get("source") # e.g. "live" or "dashboard"
    p = get_pipeline(course_id)

    # Get all submissions (including rejected ones)
    submissions = []
    for sub in p._submissions:
        # Filter by source if requested
        if source_filter and sub.source != source_filter:
            continue
            
        submissions.append({
            "text": sub.text,
            "accepted": sub.accepted,
            "source": sub.source,
            "rejection_reason": sub.rejection_reason,
            "file_url": sub.file_url,
            "link": sub.link,
            "status": sub.status,
            "resolution_text": sub.resolution_text,
            "resolution_file_url": sub.resolution_file_url,
            "resolution_audio_url": sub.resolution_audio_url
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
