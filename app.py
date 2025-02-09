from flask import Flask, render_template, request, jsonify
from main import UWaterlooAPI
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
api = UWaterlooAPI()

# Store subscriptions in memory (in production, use a database)
subscriptions = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/check-availability', methods=['POST'])
def check_availability():
    data = request.json
    term_code = data.get('term')
    subject = data.get('subject').upper()
    catalog_number = data.get('catalogNumber')
    email = data.get('email')

    try:
        course_data = api.get_course_schedule(term_code, subject, catalog_number)
        
        if not course_data:
            return jsonify({
                'success': False,
                'message': 'Unable to fetch course data'
            })

        # Format course data for display
        formatted_sections = []
        for section in course_data:
            capacity = section.get('maxEnrollmentCapacity', 0)
            enrolled = section.get('enrolledStudents', 0)
            available = capacity - enrolled
            
            schedule_info = section.get('scheduleData', [{}])[0]
            time_str = 'N/A'
            if schedule_info.get('classMeetingStartTime') and schedule_info.get('classMeetingEndTime'):
                start_time = datetime.fromisoformat(schedule_info['classMeetingStartTime'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(schedule_info['classMeetingEndTime'].replace('Z', '+00:00'))
                time_str = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"

            formatted_sections.append({
                'section': section.get('classSection', 'N/A'),
                'component': section.get('courseComponent', 'N/A'),
                'classNumber': section.get('classNumber', 'N/A'),
                'capacity': capacity,
                'enrolled': enrolled,
                'available': available,
                'status': "OPEN" if available > 0 else "FULL",
                'location': schedule_info.get('locationName', 'N/A'),
                'time': time_str
            })

        # Add subscription if requested
        if email:
            subscriptions.append({
                'email': email,
                'term': term_code,
                'subject': subject,
                'catalogNumber': catalog_number
            })

        return jsonify({
            'success': True,
            'sections': formatted_sections
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

if __name__ == '__main__':
    app.run(debug=True) 