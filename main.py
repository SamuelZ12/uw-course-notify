import os
import requests
import time
from datetime import datetime
import logging
from typing import Dict, List
from dotenv import load_dotenv
from prettytable import PrettyTable

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class UWaterlooAPI:
    def __init__(self):
        self.api_key = os.getenv('UWATERLOO_API_KEY')
        if not self.api_key:
            raise ValueError("UWATERLOO_API_KEY environment variable is not set")
        self.base_url = 'https://openapi.data.uwaterloo.ca'
        self.headers = {
            'x-api-key': self.api_key,
            'accept': 'application/json'
        }

    def get_terms(self) -> Dict:
        """
        Fetch current terms
        """
        endpoint = '/Terms'
        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching terms: {e}")
            return None

    def get_course_schedule(self, term_code: str, subject: str, catalog_number: str) -> Dict:
        """
        Fetch course schedule data using the ClassSchedules endpoint
        """
        endpoint = f'/v3/ClassSchedules/{term_code}/{subject}/{catalog_number}'
        try:
            url = f"{self.base_url}{endpoint}"
            print(f"Requesting URL: {url}")  # Debug print
            response = requests.get(
                url,
                headers=self.headers
            )
            print(f"Response status code: {response.status_code}")  # Debug print
            if response.status_code != 200:
                print(f"Response content: {response.text}")  # Debug print
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching course data: {e}")
            return None

class NotificationManager:
    def __init__(self):
        self.subscribers = {}  # Dict to store user subscriptions

    def add_subscription(self, email: str, course_info: Dict):
        """
        Add a new course subscription for a user
        """
        if email not in self.subscribers:
            self.subscribers[email] = []
        self.subscribers[email].append(course_info)

    def notify_user(self, email: str, course_info: Dict):
        """
        Send notification to user about course availability
        """
        # TODO: Implement email notification
        logging.info(f"Notifying {email} about available course: {course_info}")

def display_course_info(course_data: List[Dict]):
    """
    Display course information in a formatted table
    """
    if not course_data:
        print("No course data available")
        return

    table = PrettyTable()
    table.field_names = [
        "Section", "Class Number", "Component", 
        "Capacity", "Enrolled", "Available", "Status",
        "Location", "Time"
    ]

    for section in course_data:
        try:
            capacity = section.get('maxEnrollmentCapacity', 0)
            enrolled = section.get('enrolledStudents', 0)
            available = capacity - enrolled
            status = "OPEN" if available > 0 else "FULL"
            
            # Get schedule information
            schedule_info = section.get('scheduleData', [{}])[0]
            location = schedule_info.get('locationName', 'N/A')
            
            # Format meeting times if available
            time_str = 'N/A'
            if schedule_info.get('classMeetingStartTime') and schedule_info.get('classMeetingEndTime'):
                start_time = datetime.fromisoformat(schedule_info['classMeetingStartTime'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(schedule_info['classMeetingEndTime'].replace('Z', '+00:00'))
                time_str = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
            
            table.add_row([
                section.get('classSection', 'N/A'),
                section.get('classNumber', 'N/A'),
                section.get('courseComponent', 'N/A'),
                capacity,
                enrolled,
                available,
                status,
                location,
                time_str
            ])
        except Exception as e:
            logging.error(f"Error processing section data: {e}")
            continue

    print("\nCS 136 Course Availability:")
    print(table)
    print(f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def get_current_term(api: UWaterlooAPI) -> str:
    """
    Get the current term code from the API
    """
    terms = api.get_terms()
    if not terms:
        return None
    
    # Find the current term
    for term in terms:
        if term.get('isCurrent', False):
            return str(term.get('termCode'))
    
    # If no current term found, return the most recent term
    if terms:
        return str(terms[0].get('termCode'))
    return None

def main():
    api = UWaterlooAPI()
    notification_manager = NotificationManager()
    
    # Spring 2024
    term_code = '1251'
    subject = 'CS'
    catalog_number = '136'

    print(f"\nMonitoring CS 136 availability for term {term_code} (Spring 2024)")
    print("Press Ctrl+C to stop.")
    print("Checking every 30 seconds...")

    try:
        while True:
            course_data = api.get_course_schedule(term_code, subject, catalog_number)
            
            if course_data:
                if isinstance(course_data, list):
                    display_course_info(course_data)
                else:
                    print(f"Unexpected API response format: {course_data}")
            else:
                print("Unable to fetch course data. Retrying...")
                print("Debug info:")
                print(f"Term: {term_code}")
                print(f"Subject: {subject}")
                print(f"Catalog Number: {catalog_number}")

            time.sleep(30)  # Check every 30 seconds

    except KeyboardInterrupt:
        print("\nStopping course monitoring...")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise e

if __name__ == "__main__":
    main()
