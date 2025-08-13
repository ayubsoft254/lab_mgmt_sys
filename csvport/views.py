import csv
import warnings
import requests
import urllib3
from django.http import HttpResponse
from django.views import View
import json


class AllocationCSVView(View):
    def get(self, request, reg_no=None):
        reg_no = reg_no or request.GET.get("reg_no")
        if not reg_no:
            return HttpResponse("Missing registration number", status=400)

        API_BASE = "https://portal2.ttu.ac.ke"
        token_url = f"{API_BASE}/api/token/"
        api_url = f"{API_BASE}/api/allocations/?reg_no={reg_no}"

        credentials = {
            "username": "hostel-checker",
            "password": "rt0[([etx7gvOnSOx4@[CzaAmS][%{"
        }

        warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)

        try:
            # Step 1: Get token
            token_response = requests.post(token_url, json=credentials, verify=False, timeout=10)
            token_response.raise_for_status()
            tokens = token_response.json()

            # Debug: log token response
            print("TOKEN RESPONSE:", json.dumps(tokens, indent=2))

            if "access" not in tokens:
                return HttpResponse(f"Authentication failed: {tokens}", status=401)

            access_token = tokens["access"]

            # Step 2: Call API with Authorization header
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            print("API URL:", api_url)
            print("HEADERS:", headers)

            response = requests.get(api_url, headers=headers, verify=False, timeout=10)

            # Debug: log raw API response
            print("STATUS CODE:", response.status_code)
            print("RAW RESPONSE TEXT:", response.text)

            response.raise_for_status()
            student_data = response.json()

        except requests.RequestException as e:
            return HttpResponse(f"Error fetching data: {e}", status=500)

        if not student_data:
            return HttpResponse("No data found", status=404)

        # Normalize data
        if isinstance(student_data, dict):
            if "results" in student_data:
                student_data = student_data["results"]
            elif "data" in student_data:
                student_data = student_data["data"]
            else:
                student_data = [student_data]

        if not isinstance(student_data, list):
            return HttpResponse("Unexpected data format", status=500)

        # Step 3: Convert to CSV
        response_csv = HttpResponse(content_type="text/csv")
        safe_reg_no = reg_no.replace("/", "_").replace(" ", "_")
        response_csv["Content-Disposition"] = f'attachment; filename="allocation_{safe_reg_no}.csv"'

        writer = csv.writer(response_csv)
        headers_list = list(student_data[0].keys())
        writer.writerow(headers_list)

        for item in student_data:
            writer.writerow([item.get(h, "") for h in headers_list])

        return response_csv