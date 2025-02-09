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
    section_number = data.get('section')
    email = data.get('email')

    try:
        course_data = api.get_course_schedule(term_code, subject, catalog_number)
        
        if not course_data:
            return jsonify({
                'success': False,
                'message': 'Unable to fetch course data'
            })

        print("API Response:", course_data)  # Debug print
        
        formatted_sections = []
        for section in course_data:
            if section_number and str(section.get('classSection', '')) != str(section_number):
                continue

            # Basic section info
            capacity = section.get('maxEnrollmentCapacity', 0)
            enrolled = section.get('enrolledStudents', 0)
            available = capacity - enrolled

            # Schedule information
            schedule_data = section.get('scheduleData', [])
            schedule_info = {}
            time_str = 'TBA'
            location = 'TBA'
            days = 'TBA'
            
            if schedule_data:
                schedule_info = schedule_data[0]
                # Get location
                location = schedule_info.get('locationName', 'TBA')
                
                # Get meeting times
                if schedule_info.get('classMeetingStartTime') and schedule_info.get('classMeetingEndTime'):
                    start_time = datetime.fromisoformat(schedule_info['classMeetingStartTime'].replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(schedule_info['classMeetingEndTime'].replace('Z', '+00:00'))
                    time_str = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
                
                # Get meeting days
                days = schedule_info.get('classMeetingDayPatternCode', 'TBA')

            # Instructor information
            instructor_data = section.get('instructorData', [])
            instructors = []
            if instructor_data:
                for instructor in instructor_data:
                    first_name = instructor.get('instructorFirstName', '')
                    last_name = instructor.get('instructorLastName', '')
                    role = instructor.get('instructorRoleCode', '')
                    if first_name or last_name:
                        full_name = f"{first_name} {last_name}".strip()
                        if role:
                            instructors.append(f"{full_name} ({role})")
                        else:
                            instructors.append(full_name)

            instructor_str = ', '.join(instructors) if instructors else 'TBA'

            formatted_sections.append({
                'section': section.get('classSection', 'N/A'),
                'component': section.get('courseComponent', 'LEC'),
                'classNumber': section.get('classNumber', 'N/A'),
                'capacity': capacity,
                'enrolled': enrolled,
                'available': available,
                'status': "OPEN" if available > 0 else "FULL",
                'location': location,
                'time': time_str,
                'instructor': instructor_str,
                'days': days,
                'enrollConsentRequired': section.get('enrollConsentDescription', 'None'),
                'dropConsentRequired': section.get('dropConsentDescription', 'None')
            })

        # Add subscription if requested
        if email:
            subscriptions.append({
                'email': email,
                'term': term_code,
                'subject': subject,
                'catalogNumber': catalog_number,
                'section': section_number
            })

        return jsonify({
            'success': True,
            'sections': formatted_sections
        })

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/subscribe-notification', methods=['POST'])
def subscribe_notification():
    data = request.json
    email = data.get('email')
    term_code = data.get('term')
    subject = data.get('subject')
    catalog_number = data.get('catalogNumber')
    section = data.get('section')

    if not all([email, term_code, subject, catalog_number, section]):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        })

    # Add to subscriptions
    subscription = {
        'email': email,
        'term': term_code,
        'subject': subject,
        'catalogNumber': catalog_number,
        'section': section,
        'timestamp': datetime.now().isoformat()
    }
    
    # Check if subscription already exists
    if any(sub['email'] == email and 
           sub['term'] == term_code and 
           sub['subject'] == subject and 
           sub['catalogNumber'] == catalog_number and 
           sub['section'] == section 
           for sub in subscriptions):
        return jsonify({
            'success': False,
            'message': 'You are already subscribed to notifications for this section'
        })

    subscriptions.append(subscription)
    
    return jsonify({
        'success': True,
        'message': f'You will be notified when section {section} becomes available'
    })

if __name__ == '__main__':
    app.run(debug=True) 