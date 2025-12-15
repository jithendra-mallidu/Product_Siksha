import requests
import json
import sys

BASE_URL = 'http://127.0.0.1:5001/api'
EMAIL = 'testuser@example.com'
PASSWORD = 'password456' # Updated password from previous step

def run_test():
    # 1. Login
    print("1. Logging in...")
    try:
        resp = requests.post(f'{BASE_URL}/login', json={'email': EMAIL, 'password': PASSWORD})
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return
        token = resp.json()['token']
        print("   Login successful.")
    except Exception as e:
        print(f"   Failed to connect: {e}")
        return

    headers = {'Authorization': f'Bearer {token}'}

    # 2. Get questions for a category (Product Design)
    print("\n2. Fetching initial questions...")
    resp = requests.get(f'{BASE_URL}/questions/product-design', headers=headers)
    if resp.status_code != 200:
        print(f"Fetch failed: {resp.text}")
        return
    
    data = resp.json()
    questions = data['questions']
    print(f"   Fetched {len(questions)} questions.")
    
    if not questions:
        print("   No questions found. Cannot proceed.")
        return

    # Pick the first question to toggle
    q1 = questions[0]
    q1_id = q1['id']
    print(f"   Target Question ID: {q1_id}, Current Status: {q1.get('is_completed', False)}")

    # 3. Toggle Completion
    print(f"\n3. Toggling completion for QID {q1_id}...")
    resp = requests.post(f'{BASE_URL}/questions/{q1_id}/toggle', headers=headers)
    if resp.status_code != 200:
        print(f"Toggle failed: {resp.text}")
        return
    
    toggle_data = resp.json()
    print(f"   Toggle response: {toggle_data}")
    
    # 4. Fetch again and verify order
    print("\n4. Verifying sorting order...")
    resp = requests.get(f'{BASE_URL}/questions/product-design', headers=headers)
    data = resp.json()
    new_questions = data['questions']
    
    # The toggled question should now be in the "Completed" section.
    # Logic: Completed (Old->New), Uncompleted.
    # Since we just marked it completed, it should be the LAST of the completed block (most recent).
    # IF it was the only completed one, it should be first.
    
    found_q = next((q for q in new_questions if q['id'] == q1_id), None)
    if found_q:
        print(f"   Question found in new list. Completed: {found_q['is_completed']}")
        if found_q['is_completed']:
            print("   SUCCESS: Question marked as completed.")
        else:
            print("   FAILURE: Question not marked completed.")
    else:
        print("   FAILURE: Question not found in list.")

    # Check order
    # First item should be a completed question (if any exist)
    first_q = new_questions[0]
    print(f"   First question in list ID: {first_q['id']}, Completed: {first_q.get('is_completed')}")

if __name__ == '__main__':
    run_test()
