from flask import Flask, request, jsonify
from flask_cors import CORS
from ai_pipeline.pipeline import DoubtPipeline

app = Flask(__name__)
CORS(app)

pipeline = DoubtPipeline()
pipeline.set_topic("General Classroom Session")

@app.route('/submit_doubt', methods=['POST'])
def submit():
    data = request.json
    text = data.get("doubt", "")
    if not text:
        return jsonify({"error": "No doubt text provided"}), 400
        
    result = pipeline.submit_doubt(text)
    
    # After submission, get the clustered summary to dump to file
    output = pipeline.get_clustered_summary()
    
    with open("filtered_doubts.txt", "w", encoding="utf-8") as f:
        f.write(f"Total Accepted: {output.total_accepted}\n")
        f.write(f"Total Rejected: {output.total_rejected}\n\n")
        
        f.write("--- ACCEPTED DOUBTS CLUSTERS ---\n")
        for c in output.clusters:
            f.write(f"Cluster {c.cluster_id} ({c.count} doubts) Summary: {c.summary}\n")
            for d in c.doubts:
                f.write(f" - {d}\n")
            f.write("\n")
            
        f.write("--- UNCLUSTERED ---\n")
        for u in output.unclustered:
            f.write(f" - {u}\n")
            
        f.write("\n--- ALL SUBMISSIONS ---\n")
        for sub in pipeline._submissions:
            status = "ACCEPTED" if sub.accepted else f"REJECTED: {sub.rejection_reason}"
            f.write(f"[{status}] {sub.text}\n")
            
    return jsonify({
        "success": True,
        "accepted": result.accepted,
        "reason": result.rejection_reason
    })

if __name__ == '__main__':
    print("Starting Amigo AI Backend on http://localhost:5000")
    app.run(port=5000, debug=True)
