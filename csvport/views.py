import csv
import requests
import warnings
from django.http import HttpResponse
from django.views import View
import urllib3


class AllocationCSVView(View):
    def get(self, request):
        # Get reg_no from query parameter
        reg_no = request.GET.get("reg_no")
        if not reg_no:
            return HttpResponse("Missing 'reg_no' query parameter", status=400)

        API_BASE = "https://portal2.ttu.ac.ke"
        token_url = f"{API_BASE}/api/token/"
        data_url = f"{API_BASE}/api/allocation/?reg_no={reg_no}"

        credentials = {
            "username": "hostel-checker",
            "password": "rt0[([etx7gvOnSOx4@[CzaAmS][%{"
        }

        # Disable SSL verification warnings
        warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)

        try:
            # Step 1: Get access token
            token_res = requests.post(token_url, json=credentials, verify=False, timeout=10)
            token_res.raise_for_status()
            tokens = token_res.json()

            if "access" not in tokens:
                return HttpResponse("Authentication failed: No access token", status=401)

            access_token = tokens["access"]

            # Step 2: Fetch student data
            headers = {"Authorization": f"Bearer {access_token}"}
            data_res = requests.get(data_url, headers=headers, verify=False, timeout=10)
            data_res.raise_for_status()
            data = data_res.json()

        except requests.RequestException as e:
            return HttpResponse(f"Error fetching data: {e}", status=500)

        # Ensure the data is a list (for CSV)
        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list) or not data:
            return HttpResponse("No valid data returned", status=404)

        # Step 3: Create CSV response
        response_csv = HttpResponse(content_type="text/csv")
        safe_reg_no = reg_no.replace("/", "_").replace(" ", "_")
        response_csv["Content-Disposition"] = f'attachment; filename="allocation_{safe_reg_no}.csv"'

        writer = csv.writer(response_csv)
        headers = data[0].keys()
        writer.writerow(headers)
        for item in data:
            writer.writerow(item.values())

        return response_csv